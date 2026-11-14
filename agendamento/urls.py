from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('especialidades/', views.especialidades_view, name='especialidades'),
    path('minhas-consultas/', views.minhas_consultas, name='minhas_consultas'),
    path('cancelar-consulta/<int:consulta_id>/', views.cancelar_consulta, name='cancelar_consulta'),
    path('login/', views.login_view, name='login'),
    path('cadastro-profissional/', views.cadastro_profissional, name='cadastro_profissional'),
    path('painel-medico/', views.painel_medico, name='painel_medico'),
    path('painel-medico/consulta/<int:consulta_id>/status/', views.atualizar_status_consulta, name='atualizar_status_consulta'),
    path('monitoramento/', views.monitoramento_admin, name='monitoramento_admin'),
    path('logout/', views.logout_view, name='logout'),
    path(
        'recuperar-senha/',
        auth_views.PasswordResetView.as_view(
            template_name='agendamento/recuperar_senha.html',
            email_template_name='agendamento/emails/password_reset_email.txt',
            subject_template_name='agendamento/emails/password_reset_subject.txt',
            success_url=reverse_lazy('recuperar_senha_enviado'),
        ),
        name='recuperar_senha',
    ),
    path(
        'recuperar-senha/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='agendamento/recuperar_senha_enviado.html'
        ),
        name='recuperar_senha_enviado',
    ),
    path(
        'recuperar-senha/confirmar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='agendamento/recuperar_senha_confirmar.html',
            success_url=reverse_lazy('recuperar_senha_concluido'),
        ),
        name='recuperar_senha_confirmar',
    ),
    path(
        'recuperar-senha/concluido/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='agendamento/recuperar_senha_concluido.html'
        ),
        name='recuperar_senha_concluido',
    ),
    path('agendar/<int:profissional_id>/', views.agendar, name='agendar_consulta'),
    path('api/horarios/<int:profissional_id>/', views.api_horarios, name='api_horarios'),
]
