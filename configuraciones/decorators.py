from django.shortcuts import redirect
from django.contrib import messages

def admin_requerido(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Administrador').exists():
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "No tienes permisos para acceder a esta área.")
            return redirect('pantalla_pos')
    return wrapper
