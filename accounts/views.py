from django.shortcuts            import render, redirect, get_object_or_404
from django.contrib.auth         import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms   import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms                      import CustomUserCreationForm, CSVResultForm
from .models import CSVResult
from ecg.models            import ECGSignal, AnalysisResult
from ecg.ml                import run_ecg_analysis
import csv
import json





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



@login_required
def add_result_view(request):
    if request.method == 'POST':
        form = CSVResultForm(request.POST, request.FILES)
        if form.is_valid():
            # 1) save the CSVResult
            result = form.save(commit=False)
            result.owner = request.user
            result.save()

            # 2) run ML analysis
            stats = run_ecg_analysis(result.csv_file.path)

            # 3) store stats on CSVResult
            result.analysis = stats
            result.save()

            # 4) mirror into the ecg app
            ecg_signal = ECGSignal.objects.create(
                owner=request.user,
                file=result.csv_file     # ← if your ECGSignal model uses a different field name, swap this
            )
            AnalysisResult.objects.create(
                signal=ecg_signal,
                result_json=stats
            )

            return redirect('accounts:your_results')
    else:
        form = CSVResultForm()
    return render(request, 'accounts/add_result.html', {'form': form})


@login_required
def your_results_view(request):
    qs = CSVResult.objects.filter(owner=request.user).order_by('-uploaded_at')
    results = []
    for r in qs:
        # try to find the matching ECGSignal
        try:
            ecg = ECGSignal.objects.get(file=r.csv_file.name, owner=request.user)
            ar = AnalysisResult.objects.filter(signal=ecg).order_by('-id').first()
            analysis = ar.result_json if ar else None
        except ECGSignal.DoesNotExist:
            analysis = None

        # temporarily attach it
        r.ml_stats = analysis
        results.append(r)

    return render(request, 'accounts/your_results.html', {
        'results': results,
    })



@login_required
def result_detail_view(request, pk):
    # 1) fetch the CSVResult (or 404)
    result = get_object_or_404(CSVResult, pk=pk, owner=request.user)

    # 2) load raw samples from the CSV file
    samples = []
    with open(result.csv_file.path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            # assume one column of floats; adjust if multiple cols
            try:
                samples.append(float(row[0]))
            except (ValueError, IndexError):
                continue

    # 3) prepare JSON for Chart.js
    signal_json = json.dumps(samples)

    # 4) stats are already in result.analysis
    stats = result.analysis or {}

    return render(request, 'accounts/result_detail.html', {
        'result': result,
        'signal_json': signal_json,
        'stats': stats,
    })
