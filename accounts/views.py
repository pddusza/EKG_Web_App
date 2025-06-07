from django.shortcuts            import render, redirect, get_object_or_404
from django.contrib.auth         import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms   import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms                      import CustomUserCreationForm, CSVResultForm
from .models import CSVResult
from ecg.models            import ECGSignal, AnalysisResult
from ecg.ml                import run_ecg_analysis, predict_from_csv
import csv
import json
from django.core.paginator import Paginator
from .models                    import Profile

app_name = 'accounts'

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()       # safely returns the authenticated User
            auth_login(request, user)    # sets up session
            return redirect('accounts:mainscreen')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()            # <-- writes to auth_user
            auth_login(request, user)     # optional: log them in
            return redirect("accounts:login")      # or "ecg:history", whichever you prefer
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})

def mainscreen_view(request):
    return render(request, 'accounts/mainscreen.html')

def user_logout(request):
    auth_logout(request)
    return redirect('accounts:login')


def profile_view(request):
    user = request.user
    profile = user.profile
    if request.method == 'POST':
        # Aktualizacja danych
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        profile.first_name = request.POST.get('first_name', profile.first_name)
        profile.last_name = request.POST.get('last_name', profile.last_name)
        profile.bio = request.POST.get('bio', profile.bio)
        profile.avatar = request.POST.get('avatar', profile.avatar)
        user.save()
        profile.save()
        return redirect('mainscreen')
    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile': profile,
    })


def settings_view(request):

    return render(request, 'accounts/settings.html')

def add_result_view(request):

    return render(request, 'accounts/add_result.html')

def your_results_view(request):

    return render(request, 'accounts/your_results.html')

def account_type_view(request):
    return render(request, 'accounts/account_type.html')

def register_patient_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # populate profile fields
            p = user.profile
            p.first_name      = form.cleaned_data['first_name']
            p.last_name       = form.cleaned_data['last_name']
            p.pesel           = form.cleaned_data['pesel']
            p.birth_date      = form.cleaned_data['birth_date']
            p.medical_history = form.cleaned_data['medical_history']
            # privileges stay: is_patient=True
            p.save()
            auth_login(request, user)
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register_patient.html", {"form": form})


def register_doctor_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            p = user.profile
            p.first_name     = form.cleaned_data['first_name']
            p.last_name      = form.cleaned_data['last_name']
            p.license_number = form.cleaned_data['license_number']
            p.bio            = form.cleaned_data['bio']
            # set doctor+admin for now
            p.is_patient = False
            p.is_doctor  = True
            p.is_admin   = True
            p.save()
            auth_login(request, user)
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register_doctor.html", {"form": form})




import math

def _sanitize_for_json(obj):
    """
    Recursively replace any float that is NaN/Inf with None,
    so that the resulting structure is valid JSON.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj

@login_required
def add_result_view(request):
    if request.method == 'POST':
        form = CSVResultForm(request.POST, request.FILES)
        if form.is_valid():
            # 1) Save the uploaded file record
            result = form.save(commit=False)
            result.owner = request.user
            result.save()

            # 2) Run NeuroKit2 analysis
            raw_stats = run_ecg_analysis(result.csv_file.path)

            # 3) Run TensorFlow/Keras classification on same CSV
            #    We wrap in try/except so that any classification error
            #    doesn’t block saving NeuroKit2 results.
            try:
                classification = predict_from_csv(result.csv_file.path)
            except Exception as e:
                # On model‐loading or shape‐mismatch errors, store error message
                classification = {'error': str(e)}

            # 4) Merge classification into the same stats dict
            raw_stats['classification'] = classification

            # 5) Sanitize entire JSON (replacing NaN/Inf→None)
            clean_stats = _sanitize_for_json(raw_stats)

            # 6) Persist JSON on CSVResult
            result.analysis = clean_stats
            result.save()

            # 7) Mirror into ecg app:
            # Create AnalysisResult using the same clean_stats (which now includes 'classification')
            ecg_signal = ECGSignal.objects.create(
                owner=request.user,
                file=result.csv_file
            )
            AnalysisResult.objects.create(
                signal=ecg_signal,
                result_json=clean_stats
            )

            return redirect('accounts:your_results')
    else:
        form = CSVResultForm()

    return render(request, 'accounts/add_result.html', {'form': form})

@login_required
def your_results_view(request):
    qs = CSVResult.objects.filter(owner=request.user).order_by('-uploaded_at')
    record_number = request.GET.get('record_number')
    name_filter = request.GET.get('name')
    page = request.GET.get('page', 1)  #
    if name_filter:
        qs = qs.filter(title__icontains=name_filter)
    results = []
    page_number = request.GET.get('page', '1')
    for r in qs:
        try:
            ecg = ECGSignal.objects.get(file=r.csv_file.name, owner=request.user)
            ar = AnalysisResult.objects.filter(signal=ecg).order_by('-id').first()
            analysis = ar.result_json if ar else None
        except ECGSignal.DoesNotExist:
            analysis = None

        r.ml_stats = analysis
        results.append(r)
    if record_number:
        try:
            index = int(record_number) - 1
            if 0 <= index < len(results):
                results = [results[index]]
                page = None  
            else:
                results = []
        except ValueError:
            results = []
        return render(request, 'accounts/your_results.html', {
            'results': results,
            'page_obj': None,
            'page': None,
        })
    paginator = Paginator(results, 3)
    page_obj = paginator.get_page(page)
    offset = (page_obj.number - 1) * 3
    return render(request, 'accounts/your_results.html', {
        'results': page_obj.object_list,
        'page_obj': page_obj,
        'current_page': page_obj.number,
        'offset': offset,
    })


@login_required
def result_detail_view(request, pk):
    result = get_object_or_404(CSVResult, pk=pk, owner=request.user)
    samples = []
    with open(result.csv_file.path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            try: samples.append(float(row[0]))
            except: pass
    signal_json = json.dumps(samples)

    analysis     = result.analysis or {}
    stats        = analysis.get('stats', {})
    rpeaks       = analysis.get('rpeaks', [])
    heart_rate   = analysis.get('heart_rate', [])
    hrv_time     = analysis.get('hrv_time', {})
    hrv_freq     = analysis.get('hrv_frequency', {})
    hrv_nonlin   = analysis.get('hrv_nonlinear', {})
    morphology   = analysis.get('morphology', {})
    classification = analysis.get('classification', {})

    return render(request, 'accounts/result_detail.html', {
        'result':       result,
        'signal_json':  signal_json,
        'stats':        stats,
        'rpeaks':       rpeaks,
        'heart_rate':   heart_rate,
        'hrv_time':     hrv_time,
        'hrv_frequency':hrv_freq,
        'hrv_nonlinear':hrv_nonlin,
        'morphology':   morphology,
        'classification': classification,
    })