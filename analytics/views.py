import pandas as pd
from django.http import HttpResponse
import matplotlib.pyplot as plt
from io import BytesIO

def export_csv(request):
    df = pd.DataFrame([{'time':'now','value':1}])
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="export.csv"'
    df.to_csv(resp, index=False)
    return resp

def chart_png(request):
    fig, ax = plt.subplots()
    ax.plot([1,2,3],[3,1,4])
    buf = BytesIO()
    fig.savefig(buf, format='png')
    return HttpResponse(buf.getvalue(), content_type='image/png')