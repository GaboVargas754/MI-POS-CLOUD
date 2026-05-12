from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from core.utils import get_config_context

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def dashboard(request):
    return render(request, 'inventario/dashboard.html', get_config_context('Inventario', 'border-purple-600'))
