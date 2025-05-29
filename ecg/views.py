from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import UploadECGForm
from .models import ECGSignal, AnalysisResult
from .ml import run_ecg_analysis

@login_required
def upload_ecg(request):
    if request.method == 'POST':
        form = UploadECGForm(request.POST, request.FILES)
        if form.is_valid():
            # 1) save the raw signal record
            ecg = form.save(commit=False)
            ecg.owner = request.user
            ecg.save()  # <-- creates a row in ecg_ecgsignal

            # 2) run your ML helper
            stats = run_ecg_analysis(ecg.file.path)

            # 3) persist the analysis results
            AnalysisResult.objects.create(
                signal=ecg,
                result_json=stats
            )  # <-- creates a row in ecg_analysisresult

            # 4) redirect to history (or wherever you want)
            return redirect('ecg:history')
    else:
        form = UploadECGForm()

    return render(request, 'ecg/upload.html', {'form': form})



@login_required
def history(request):
    signals = ECGSignal.objects.filter(owner=request.user)
    return render(request, 'ecg/history.html', {'signals': signals})

@login_required
def detail(request, pk):
    ecg    = get_object_or_404(ECGSignal, pk=pk, owner=request.user)
    result = get_object_or_404(AnalysisResult, signal=ecg)
    return render(request, 'ecg/detail.html', {
        'signal': ecg,
        'result': result.result_json,
    })