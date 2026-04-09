from django.http import HttpResponse
from django.shortcuts import redirect

def unauthentificated_user(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        else:
            return view_func(request,*args,**kwargs)
    return wrapper_func

def allowed_permisstion(allowed_roles=[]):
    def administration(view_func):
        def wrapper_func(request,*args,**kwargs):
                #print('working',allowed_roles)
                groups=None
                if request.user.groups.exists():
                    groups=request.user.groups.all()[0].name
                if groups in allowed_roles:
                    return view_func(request,*args,**kwargs)
                else:
                   return HttpResponse('You are not authorized to see this page')
        return wrapper_func
    return administration