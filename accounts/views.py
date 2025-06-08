import os, io, uuid
from django.conf                 import settings
from django.shortcuts            import render, redirect, get_object_or_404
from django.contrib.auth         import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms   import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .forms                      import CustomUserCreationForm, CSVResultForm, ProfileForm
from .models import CSVResult
from ecg.models            import ECGSignal, AnalysisResult
from ecg.ml                import run_ecg_analysis, predict_from_csv
import csv
import json
from django.core.paginator import Paginator
from .models                    import Profile
from PIL                 import Image
from django.core.files.base    import ContentFile
from django.contrib import messages
app_name = 'accounts'

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            profile = user.profile
            if profile.is_doctor or profile.is_patient:
                return redirect('accounts:mainscreen')
            return redirect('accounts:login')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()            # <-- writes to auth_user
            auth_login(request, user)     # optional: log them in
            return redirect("accounts:login")      # or "ecg:history", whichever you prefer
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})

@login_required
def mainscreen_view(request):
    return render(request, 'accounts/mainscreen.html')

def user_logout(request):
    auth_logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    user    = request.user
    profile = user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Update User
            user.username = form.cleaned_data['username']
            user.email    = form.cleaned_data['email']
            user.save()
            # Save Profile fields
            profile = form.save(commit=False)
            avatar_file = form.cleaned_data.get('avatar_upload')
            if avatar_file:
                profile.avatar = avatar_file
            profile.save()
            # Crop
            offsetX = form.cleaned_data['offsetX']
            offsetY = form.cleaned_data['offsetY']
            scale   = form.cleaned_data['scale']
            _crop_and_save(profile, offsetX, offsetY, scale)
            profile.save()
            return redirect('accounts:mainscreen')
    else:
        form = ProfileForm(
            initial={'username': request.user.username,
                     'email':    request.user.email,
                     'offsetX':  0,'offsetY':0,'scale':1.0},
            instance=profile
        )
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})

def _crop_and_save(profile, offsetX, offsetY, scale):
    """
    Open profile.avatar, resize and crop to 120×120, then
    overwrite profile.avatar with a new UUID file in avatars_users.
    """
    img_path = profile.avatar.path
    with Image.open(img_path) as img:
        # 1) Resize
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 2) Centered crop box + offsets
        frame = 120
        cx = new_w//2 + offsetX
        cy = new_h//2 + offsetY
        left   = max(0, cx - frame//2)
        top    = max(0, cy - frame//2)
        right  = min(new_w, left + frame)
        bottom = min(new_h, top  + frame)
        cropped = img.crop((left, top, right, bottom))

        # 3) Write into buffer
        buf = io.BytesIO()
        cropped.save(buf, format='PNG')
        buf.seek(0)

        # 4) New UUID file path
        fname = f"{uuid.uuid4().hex}.png"

        # 5) Remove old file & save new one
        profile.avatar.delete(save=False)
        profile.avatar.save(fname,ContentFile(buf.read()),save=False)




def settings_view(request):
    return render(request, 'accounts/settings.html')

def your_results_view(request):

    return render(request, 'accounts/your_results.html')

def account_type_view(request):
    return render(request, 'accounts/account_type.html')

@login_required
def choose_patient_view(request):
    if request.method == 'POST':
        pesel = request.POST.get('pesel')

        try:
            profile = Profile.objects.get(pesel=pesel, is_patient=True)
        except Profile.DoesNotExist:
            messages.error(request, "Pacjent o podanym PESELu nie istnieje.")
            return redirect('accounts:choose_patient')

        if profile.doctor is not None:
            messages.warning(request, "Pacjent jest już przypisany do innego lekarza.")
            return redirect('accounts:choose_patient')

        profile.doctor = request.user
        profile.save()
        messages.success(request, f"Pacjent z PESEL {pesel} został przypisany do Ciebie.")
        return redirect('accounts:my_patients')  

    return render(request, 'accounts/choose_patient.html')

def register_patient_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            # 1) Create user & get profile
            user    = form.save()
            profile = user.profile

            # 2) Populate patient fields...
            profile.first_name      = form.cleaned_data['first_name']
            profile.last_name       = form.cleaned_data['last_name']
            profile.pesel           = form.cleaned_data['pesel']
            profile.birth_date      = form.cleaned_data['birth_date']
            profile.medical_history = form.cleaned_data['medical_history']
            profile.save()

            # 3) Determine raw avatar content: upload or stock
            upload = form.cleaned_data['avatar_upload']
            choice = form.cleaned_data['avatar_choice']
            if upload:
                raw = upload.read()
                ext = os.path.splitext(upload.name)[1]
            else:
                # stock path must include the avatars folder
                stock_path = os.path.join(settings.MEDIA_ROOT, 'avatars', choice)
                with open(stock_path, 'rb') as f:
                    raw = f.read()
                ext = os.path.splitext(choice)[1]

            # 2) Save raw into avatars_users/<uuid>.ext
            fname = f"{uuid.uuid4().hex}{ext}"
            profile.avatar.save(fname, ContentFile(raw), save=False)
            profile.save()

            # 3) Crop per hidden inputs
            try:
                scale   = float(request.POST.get('scale', 1.0))
                offsetX = int(request.POST.get('offsetX', 0))
                offsetY = int(request.POST.get('offsetY', 0))
            except ValueError:
                scale, offsetX, offsetY = 1.0, 0, 0

            _crop_and_save(profile, offsetX, offsetY, scale)
            profile.save()

            auth_login(request, user)
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register_patient.html", {"form": form})


def register_doctor_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            # 1) Create user & get profile
            user    = form.save()
            profile = user.profile

            # 2) Populate doctor fields...
            profile.first_name     = form.cleaned_data['first_name']
            profile.last_name      = form.cleaned_data['last_name']
            profile.license_number = form.cleaned_data['license_number']
            profile.bio            = form.cleaned_data['bio']
            # mark roles
            profile.is_patient = False
            profile.is_doctor  = True
            profile.is_admin   = True
            profile.save()

            # 3) Determine raw avatar bytes
            upload = form.cleaned_data['avatar_upload']
            choice = form.cleaned_data['avatar_choice']
            if upload:
                raw = upload.read()
                ext = os.path.splitext(upload.name)[1]
            else:
                stock_path = os.path.join(settings.MEDIA_ROOT, 'avatars', choice)
                with open(stock_path, 'rb') as f:
                    raw = f.read()
                ext = os.path.splitext(choice)[1]

            fname = f"{uuid.uuid4().hex}{ext}"
            profile.avatar.save(fname, ContentFile(raw), save=False)
            profile.save()

            try:
                scale   = float(request.POST.get('scale', 1.0))
                offsetX = int(request.POST.get('offsetX', 0))
                offsetY = int(request.POST.get('offsetY', 0))
            except ValueError:
                scale, offsetX, offsetY = 1.0, 0, 0

            _crop_and_save(profile, offsetX, offsetY, scale)
            profile.save()

            auth_login(request, user)
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register_doctor.html", {"form": form})


def _handle_avatar_crop(profile, offsetX, offsetY, scale):
    """
    Crop & resize the avatar to 120×120, then
    save it as a new file under media/avatars with a UUID name.
    """
    # Open either the uploaded image or the stock icon
    img_path = profile.avatar.path
    with Image.open(img_path) as img:
        # 🛠 Resize
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

        # 🛠 Compute crop box (center + offsets)
        frame = 120
        cx = new_size[0] // 2 + offsetX
        cy = new_size[1] // 2 + offsetY
        left   = max(0, cx - frame//2)
        top    = max(0, cy - frame//2)
        right  = min(new_size[0], left + frame)
        bottom = min(new_size[1], top  + frame)
        cropped = img.crop((left, top, right, bottom))

        # 🛠 Write to in-memory buffer
        buffer = io.BytesIO()
        cropped.save(buffer, format='PNG')
        buffer.seek(0)

        # 🛠 Create a new UUID filename
        filename = f"avatars/{uuid.uuid4().hex}.png"

        # 🛠 Save via Django storage and assign to profile
        file_content = ContentFile(buffer.read())
        profile.avatar.save(filename, file_content, save=False)



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
@user_passes_test(lambda u: u.profile.is_doctor)
def add_result_view(request):
    if request.method == 'POST':
        form = CSVResultForm(request.POST, request.FILES)
        if form.is_valid():
            # --- 1) find patient by PESEL under this doctor ---
            pesel = form.cleaned_data['pesel']
            try:
                profile = Profile.objects.get(
                    pesel=pesel,
                    is_patient=True,
                    doctor=request.user
                )
                patient_user = profile.user
            except Profile.DoesNotExist:
                form.add_error('pesel', "Pacjent o podanym numerze PESEL nie istnieje.")
                return render(request, 'accounts/add_result.html', {'form': form})

            # --- 2) save the CSVResult for that patient ---
            result = form.save(commit=False)
            result.owner = patient_user
            result.save()

            # --- 3) run ECG analysis & classification ---
            raw_stats = run_ecg_analysis(result.csv_file.path)
            try:
                classification = predict_from_csv(result.csv_file.path)
            except Exception as e:
                classification = {'error': str(e)}
            raw_stats['classification'] = classification

            # sanitize NaN/Inf → None
            def _sanitize(obj):
                if isinstance(obj, dict):
                    return {k:_sanitize(v) for k,v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                    return None
                return obj

            clean_stats = _sanitize(raw_stats)
            result.analysis = clean_stats
            result.save()

            # mirror into ecg app
            ecg_signal = ECGSignal.objects.create(
                owner=patient_user,
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
    # default owner is the logged-in user
    owner = request.user

    # if doctor is viewing a specific patient
    patient_id = request.GET.get('patient_id')
    if patient_id and request.user.profile.is_doctor:
        try:
            profile = Profile.objects.get(
                user__id=patient_id,
                is_patient=True,
                doctor=request.user
            )
            owner = profile.user
        except Profile.DoesNotExist:
            messages.error(request, "Nie masz dostępu do wyników tego pacjenta.")
            return redirect('accounts:my_patients')

    # fetch that owner’s results
    qs = CSVResult.objects.filter(owner=owner).order_by('-uploaded_at')

    # optional title filter
    name_filter = request.GET.get('name')
    if name_filter:
        qs = qs.filter(title__icontains=name_filter)

    # inject ML stats exactly as before
    results = []
    for r in qs:
        try:
            ecg  = ECGSignal.objects.get(file=r.csv_file.name, owner=owner)
            ar   = AnalysisResult.objects.filter(signal=ecg).order_by('-id').first()
            stats = ar.result_json if ar else None
        except ECGSignal.DoesNotExist:
            stats = None
        r.ml_stats = stats
        results.append(r)

    # record_number override
    record_number = request.GET.get('record_number')
    if record_number:
        try:
            index = int(record_number) - 1
            if 0 <= index < len(results):
                results = [results[index]]
            else:
                results = []
        except ValueError:
            results = []
        return render(request, 'accounts/your_results.html', {
            'results': results,
            'page_obj': None,
            'page': None
        })

    # pagination (3 per page)
    paginator = Paginator(results, 3)
    page_obj  = paginator.get_page(request.GET.get('page', 1))
    offset    = (page_obj.number - 1) * 3

    return render(request, 'accounts/your_results.html', {
        'results':      page_obj.object_list,
        'page_obj':     page_obj,
        'current_page': page_obj.number,
        'offset':       offset
    })


@login_required
def result_detail_view(request, pk):
    """
    Patients may only see their own results.
    Doctors may see results for any patient assigned to them.
    """
    user = request.user
    # Determine which CSVResult to fetch
    if hasattr(user, 'profile') and user.profile.is_doctor:
        # Doctor: allow if result.owner.profile.doctor == request.user
        result = get_object_or_404(
            CSVResult,
            pk=pk,
            owner__profile__doctor=user
        )
    else:
        # Patient (or other): only their own
        result = get_object_or_404(CSVResult, pk=pk, owner=user)

    # Load raw samples for the signal chart
    samples = []
    try:
        with open(result.csv_file.path, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    samples.append(float(row[0]))
                except ValueError:
                    pass
    except Exception:
        samples = []

    signal_json = json.dumps(samples)

    # Re-fetch the ML stats from AnalysisResult if you like,
    # or use result.analysis if you already stored it there.
    try:
        ecg_signal = ECGSignal.objects.get(file=result.csv_file.name, owner=result.owner)
        ar = AnalysisResult.objects.filter(signal=ecg_signal).order_by('-id').first()
        analysis = ar.result_json if ar else {}
    except ECGSignal.DoesNotExist:
        analysis = {}

    # Unpack fields for template
    stats          = analysis.get('stats', {})
    classification = analysis.get('classification', {})
    rpeaks         = analysis.get('rpeaks', [])
    heart_rate     = analysis.get('heart_rate', [])
    hrv_time       = analysis.get('hrv_time', {})
    hrv_frequency  = analysis.get('hrv_frequency', {})
    hrv_nonlinear  = analysis.get('hrv_nonlinear', {})
    morphology     = analysis.get('morphology', {})

    return render(request, 'accounts/result_detail.html', {
        'result':       result,
        'signal_json':  signal_json,
        'stats':        stats,
        'rpeaks':       rpeaks,
        'heart_rate':   heart_rate,
        'hrv_time':     hrv_time,
        'hrv_frequency':hrv_frequency,
        'hrv_nonlinear':hrv_nonlinear,
        'morphology':   morphology,
        'classification': classification,
    })

def is_doctor(user):
    return hasattr(user, 'profile') and user.profile.is_doctor

def is_patient(user):
    return hasattr(user, 'profile') and user.profile.is_patient

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import Profile  # <- dostosuj ścieżkę importu jeśli inna

@login_required
def my_patients_view(request):
    pesel_filter = request.GET.get('pesel', '')
    # only patients assigned to this doctor
    qs = Profile.objects.filter(
        is_patient=True,
        doctor=request.user
    )
    if pesel_filter:
        qs = qs.filter(pesel__icontains=pesel_filter)
    return render(request, 'accounts/my_patients.html', {
        'patients':    qs,
        'pesel_filter': pesel_filter
    })