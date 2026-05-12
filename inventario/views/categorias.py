from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from inventario.models import Categoria
from inventario.forms import CategoriaForm
from core.utils import get_config_context, get_querystring_without_page

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def lista_categorias(request):
    query = request.GET.get('q', '').strip()
    categorias_list = Categoria.objects.all().order_by('nombre')

    if query:
        categorias_list = categorias_list.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))

    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(categorias_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/categorias/lista.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
        'query': query,
        'querystring': get_querystring_without_page(request),
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def editar_categoria(request, pk=None):
    if pk:
        categoria = get_object_or_404(Categoria, pk=pk)
        titulo = "Editar Categoría"
    else:
        categoria = None
        titulo = "Nueva Categoría"

    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'inventario/categorias/formulario.html', {
        'form': form,
        'is_instance': categoria is not None,
        'titulo': titulo
    })
