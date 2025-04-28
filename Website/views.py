from django.shortcuts import render

# Create your views here.
def page1(request):
    return render(request, 'page1.html')
