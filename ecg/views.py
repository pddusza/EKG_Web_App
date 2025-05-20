from django.shortcuts import render, redirect
from .forms import UploadECGForm
from .models import ECGSignal

def upload_ecg(request):
    if request.method == 'POST':
        form = UploadECGForm(request.POST, request.FILES)
        if form.is_valid():
            ECGSignal.objects.create(
                owner=request.user.userprofile,
                file=request.FILES['file']
            )
            return redirect('ecg:history')
    else:
        form = UploadECGForm()
    return render(request, 'ecg/upload.html', {'form': form})

def history(request):
    signals = ECGSignal.objects.filter(owner=request.user.userprofile)
    return render(request, 'ecg/history.html', {'signals': signals})
