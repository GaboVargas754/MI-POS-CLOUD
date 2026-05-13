from django.contrib.auth.decorators import user_passes_test


def any_permission_required(perms, login_url=None):
    def check(user):
        return user.is_authenticated and (
            user.is_superuser or any(user.has_perm(permission) for permission in perms)
        )

    return user_passes_test(check, login_url=login_url)
