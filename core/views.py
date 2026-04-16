# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.utils import get_config_context

@login_required
def portal_principal(request):
    return render(request, 'core/portal.html', get_config_context('Portal Principal', 'border-gray-500'))
