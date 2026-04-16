from django import template

register = template.Library()

@register.filter(name='tiene_rol')
def tiene_rol(user, group_name):
    """
    Verifica si un usuario pertenece a un grupo específico.
    Uso en HTML: {% if request.user|tiene_rol:"Administrador" %}
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()
