def perfil_usuario(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        profissional = getattr(user, 'perfil_profissional', None)
        return {
            'profissional_logado': profissional,
            'eh_profissional': profissional is not None,
        }
    return {
        'profissional_logado': None,
        'eh_profissional': False,
    }
