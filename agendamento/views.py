from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Consulta, Especialidade, Profissional

HORARIOS_ATENDIMENTO = [
    '08:00', '09:00', '10:00', '11:00',
    '13:00', '14:00', '15:00', '16:00', '17:00', '18:00',
]


def _proxima_data_util(data_base):
    if data_base.weekday() == 6:  # Domingo
        return data_base + timedelta(days=1)
    return data_base


def _obter_perfil_profissional(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return user.perfil_profissional
    except Profissional.DoesNotExist:
        return None


def _validar_senha_forte(senha, senha_confirmacao):
    if senha != senha_confirmacao:
        return 'As senhas não conferem. Tente novamente.'
    if len(senha) < 8:
        return 'A senha deve ter no mínimo 8 caracteres.'
    if not any(letra.isupper() for letra in senha):
        return 'A senha deve conter pelo menos uma letra maiúscula.'
    return None


def _gerar_grade_horarios(profissional, data_alvo):
    agora_local = timezone.localtime()
    hoje = agora_local.date()
    hora_atual = agora_local.time()

    if data_alvo < hoje:
        return [], 'Não é possível agendar consultas em datas passadas.'

    if data_alvo.weekday() == 6:
        return [], 'Não realizamos atendimentos aos domingos. Escolha uma data de segunda a sábado.'

    horarios_ocupados = {
        horario.strftime('%H:%M')
        for horario in Consulta.objects.filter(
            profissional=profissional,
            data=data_alvo,
        )
        .exclude(status='CANCELADA')
        .values_list('horario', flat=True)
    }

    grade = []
    for hora_str in HORARIOS_ATENDIMENTO:
        hora_obj = datetime.strptime(hora_str, '%H:%M').time()
        horario_passado = data_alvo == hoje and hora_obj <= hora_atual
        ocupado = (hora_str in horarios_ocupados) or horario_passado
        grade.append({
            'hora': hora_str,
            'ocupado': ocupado,
            'motivo': (
                'Horário já encerrado hoje'
                if horario_passado
                else ('Horário reservado' if hora_str in horarios_ocupados else 'Disponível')
            ),
        })

    return grade, ''


def home(request):
    medicos = Profissional.objects.filter(ativo=True).select_related('especialidade')
    especialidades = Especialidade.objects.annotate(
        total_medicos=Count('profissional', filter=Q(profissional__ativo=True))
    )

    especialidade_id = request.GET.get('especialidade', '').strip()
    busca = request.GET.get('q', '').strip()
    especialidade_selecionada = None

    if especialidade_id.isdigit():
        especialidade_selecionada = int(especialidade_id)
        medicos = medicos.filter(especialidade_id=especialidade_selecionada)

    if busca:
        medicos = medicos.filter(
            Q(nome__icontains=busca)
            | Q(especialidade__nome__icontains=busca)
            | Q(registro__icontains=busca)
        )

    contexto = {
        'medicos': medicos,
        'especialidades': especialidades,
        'especialidade_selecionada': especialidade_selecionada,
        'busca': busca,
    }
    return render(request, 'agendamento/home.html', contexto)


def especialidades_view(request):
    especialidades = Especialidade.objects.prefetch_related('profissional_set').all()
    contexto = {
        'especialidades': especialidades,
    }
    return render(request, 'agendamento/especialidades.html', contexto)


def minhas_consultas(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login para visualizar suas consultas.')
        return redirect(f"{reverse('login')}?next={request.path}")

    hoje = timezone.localdate()
    todas_consultas = Consulta.objects.filter(paciente=request.user).select_related(
        'profissional', 'profissional__especialidade'
    )

    proximas_consultas = todas_consultas.filter(
        status='AGENDADA',
        data__gte=hoje,
    ).order_by('data', 'horario')

    historico_consultas = todas_consultas.exclude(
        id__in=proximas_consultas.values_list('id', flat=True)
    ).order_by('-data', '-horario')

    contexto = {
        'proximas_consultas': proximas_consultas,
        'historico_consultas': historico_consultas,
        'total_agendadas': proximas_consultas.count(),
        'total_concluidas': todas_consultas.filter(status='CONCLUIDA').count(),
        'total_canceladas': todas_consultas.filter(status='CANCELADA').count(),
    }
    return render(request, 'agendamento/minhas_consultas.html', contexto)


def cancelar_consulta(request, consulta_id):
    if not request.user.is_authenticated:
        messages.error(request, 'Você precisa estar logado para realizar esta ação.')
        return redirect('login')

    if request.method != 'POST':
        return redirect('minhas_consultas')

    consulta = get_object_or_404(Consulta, id=consulta_id, paciente=request.user)
    hoje = timezone.localdate()

    if consulta.status != 'AGENDADA':
        messages.warning(request, 'Apenas consultas agendadas podem ser canceladas.')
        return redirect('minhas_consultas')

    if consulta.data < hoje:
        messages.warning(request, 'Não é possível cancelar uma consulta de data passada.')
        return redirect('minhas_consultas')

    consulta.status = 'CANCELADA'
    consulta.save(update_fields=['status'])
    messages.success(
        request,
        f'Consulta com {consulta.profissional.nome_exibicao} em {consulta.data:%d/%m/%Y} às {consulta.horario:%H:%M} foi cancelada.',
    )
    return redirect('minhas_consultas')


def login_view(request):
    if request.user.is_authenticated:
        if _obter_perfil_profissional(request.user):
            return redirect('painel_medico')
        return redirect('home')

    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    next_seguro = (
        next_url
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
        else ''
    )

    if request.method == 'POST':
        # Cadastro de paciente (possui campo password1)
        if 'password1' in request.POST:
            nome_digitado = (request.POST.get('username') or '').strip()
            email_digitado = (request.POST.get('email') or '').strip()
            senha_digitada = request.POST.get('password1') or ''
            senha_confirmada = request.POST.get('password2') or ''

            contexto_erro = {
                'nome_salvo': nome_digitado,
                'email_salvo': email_digitado,
                'aba': 'cadastro',
                'next': next_url,
            }

            if not nome_digitado or not email_digitado:
                messages.error(request, 'Preencha seu nome de usuário e e-mail.')
                return render(request, 'agendamento/login_cadastro.html', contexto_erro)

            if User.objects.filter(username__iexact=nome_digitado).exists():
                messages.error(request, 'Este nome de usuário já está em uso. Escolha outro.')
                return render(request, 'agendamento/login_cadastro.html', contexto_erro)

            if User.objects.filter(email__iexact=email_digitado).exists():
                messages.error(request, 'Já existe uma conta cadastrada com este e-mail.')
                return render(request, 'agendamento/login_cadastro.html', contexto_erro)

            erro_senha = _validar_senha_forte(senha_digitada, senha_confirmada)
            if erro_senha:
                messages.error(request, erro_senha)
                return render(request, 'agendamento/login_cadastro.html', contexto_erro)

            novo_usuario = User.objects.create_user(
                username=nome_digitado,
                email=email_digitado,
                password=senha_digitada,
            )
            login(request, novo_usuario)
            messages.success(request, f'Conta criada com sucesso! Bem-vindo(a), {novo_usuario.username}!')
            return redirect(next_seguro or reverse('home'))

        # Login (paciente, médico ou admin)
        else:
            nome_digitado = (request.POST.get('username') or '').strip()
            senha_digitada = request.POST.get('password') or ''

            usuario_logado = authenticate(request, username=nome_digitado, password=senha_digitada)

            if usuario_logado is not None:
                login(request, usuario_logado)
                perfil_prof = _obter_perfil_profissional(usuario_logado)
                if perfil_prof:
                    messages.success(request, f'Bem-vindo(a) ao seu painel, {perfil_prof.nome_exibicao}!')
                    return redirect(next_seguro or reverse('painel_medico'))
                messages.success(request, f'Bem-vindo(a), {usuario_logado.username}!')
                return redirect(next_seguro or reverse('home'))
            else:
                messages.error(request, 'Usuário ou senha inválidos.')
                return render(
                    request,
                    'agendamento/login_cadastro.html',
                    {'login_username': nome_digitado, 'next': next_url},
                )

    return render(request, 'agendamento/login_cadastro.html', {'next': next_url})


def cadastro_profissional(request):
    if request.user.is_authenticated and _obter_perfil_profissional(request.user):
        return redirect('painel_medico')

    especialidades = Especialidade.objects.all()

    if request.method == 'POST':
        nome_profissional = (request.POST.get('nome_profissional') or '').strip()
        registro = (request.POST.get('registro') or '').strip()
        especialidade_id = (request.POST.get('especialidade') or '').strip()
        nova_especialidade = (request.POST.get('nova_especialidade') or '').strip()
        descricao_especialidade = (request.POST.get('descricao_especialidade') or '').strip()
        bio = (request.POST.get('bio') or '').strip()
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        senha1 = request.POST.get('password1') or ''
        senha2 = request.POST.get('password2') or ''

        contexto = {
            'especialidades': especialidades,
            'dados': {
                'nome_profissional': nome_profissional,
                'registro': registro,
                'especialidade': especialidade_id,
                'nova_especialidade': nova_especialidade,
                'descricao_especialidade': descricao_especialidade,
                'bio': bio,
                'username': username,
                'email': email,
            },
        }

        if not nome_profissional or not registro or not username or not email:
            messages.error(request, 'Preencha todos os campos obrigatórios de identificação e acesso.')
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        if not especialidade_id and not nova_especialidade:
            messages.error(request, 'Selecione uma especialidade existente ou informe uma nova especialidade.')
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Este nome de usuário já está em uso. Escolha outro.')
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Já existe uma conta cadastrada com este e-mail.')
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        if Profissional.objects.filter(registro__iexact=registro).exists():
            messages.error(request, 'Já existe um profissional cadastrado com este número de registro.')
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        erro_senha = _validar_senha_forte(senha1, senha2)
        if erro_senha:
            messages.error(request, erro_senha)
            return render(request, 'agendamento/cadastro_profissional.html', contexto)

        with transaction.atomic():
            if nova_especialidade:
                especialidade_obj, _ = Especialidade.objects.get_or_create(
                    nome__iexact=nova_especialidade,
                    defaults={
                        'nome': nova_especialidade,
                        'descricao': descricao_especialidade
                        or f'Atendimento especializado em {nova_especialidade} no Instituto Vitta.',
                    },
                )
            else:
                especialidade_obj = get_object_or_404(Especialidade, id=especialidade_id)

            novo_user = User.objects.create_user(
                username=username,
                email=email,
                password=senha1,
            )

            profissional = Profissional.objects.create(
                usuario=novo_user,
                nome=nome_profissional,
                registro=registro,
                especialidade=especialidade_obj,
                bio=bio,
                ativo=True,
            )

        login(request, novo_user)
        messages.success(
            request,
            f'Cadastro profissional concluído! Bem-vindo(a), {profissional.nome_exibicao}. Seu perfil já aparece na vitrine do Vitta.',
        )
        return redirect('painel_medico')

    return render(request, 'agendamento/cadastro_profissional.html', {'especialidades': especialidades})


def painel_medico(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login para acessar a área do profissional.')
        return redirect(f"{reverse('login')}?next={request.path}")

    profissional = _obter_perfil_profissional(request.user)
    if not profissional:
        messages.info(request, 'Esta área é exclusiva para profissionais cadastrados.')
        return redirect('home')

    especialidades = Especialidade.objects.all()

    # Atualização do perfil profissional via POST
    if request.method == 'POST' and request.POST.get('acao') == 'editar_perfil':
        nome = (request.POST.get('nome') or '').strip()
        registro = (request.POST.get('registro') or '').strip()
        especialidade_id = (request.POST.get('especialidade') or '').strip()
        bio = (request.POST.get('bio') or '').strip()
        ativo = request.POST.get('ativo') == 'on'

        if not nome or not registro or not especialidade_id:
            messages.error(request, 'Nome, registro profissional e especialidade são obrigatórios.')
        else:
            profissional.nome = nome
            profissional.registro = registro
            profissional.especialidade = get_object_or_404(Especialidade, id=especialidade_id)
            profissional.bio = bio
            profissional.ativo = ativo
            profissional.save()
            messages.success(request, 'Perfil profissional atualizado com sucesso!')
            return redirect('painel_medico')

    hoje = timezone.localdate()
    filtro_status = (request.GET.get('status') or 'TODAS').strip().upper()
    filtro_data = (request.GET.get('data') or '').strip()

    consultas_base = Consulta.objects.filter(profissional=profissional).select_related('paciente')

    consultas_filtradas = consultas_base
    if filtro_status in ('AGENDADA', 'CONCLUIDA', 'CANCELADA'):
        consultas_filtradas = consultas_filtradas.filter(status=filtro_status)

    if filtro_data:
        try:
            data_parsed = datetime.strptime(filtro_data, '%Y-%m-%d').date()
            consultas_filtradas = consultas_filtradas.filter(data=data_parsed)
        except ValueError:
            filtro_data = ''

    consultas_filtradas = consultas_filtradas.order_by('data', 'horario')

    contexto = {
        'profissional': profissional,
        'especialidades': especialidades,
        'consultas': consultas_filtradas,
        'filtro_status': filtro_status,
        'filtro_data': filtro_data,
        'hoje': hoje,
        'total_hoje': consultas_base.filter(data=hoje, status='AGENDADA').count(),
        'total_agendadas': consultas_base.filter(status='AGENDADA', data__gte=hoje).count(),
        'total_concluidas': consultas_base.filter(status='CONCLUIDA').count(),
        'total_canceladas': consultas_base.filter(status='CANCELADA').count(),
    }
    return render(request, 'agendamento/painel_medico.html', contexto)


def atualizar_status_consulta(request, consulta_id):
    if not request.user.is_authenticated:
        return redirect('login')

    profissional = _obter_perfil_profissional(request.user)
    if not profissional or request.method != 'POST':
        return redirect('home')

    consulta = get_object_or_404(Consulta, id=consulta_id, profissional=profissional)
    novo_status = (request.POST.get('novo_status') or '').strip().upper()

    if novo_status in ('CONCLUIDA', 'CANCELADA', 'AGENDADA'):
        consulta.status = novo_status
        try:
            consulta.save(update_fields=['status'])
        except IntegrityError:
            messages.error(request, 'Não foi possível reabrir esta consulta porque o horário já está ocupado.')
            return redirect('painel_medico')
        labels = {
            'CONCLUIDA': 'concluída',
            'CANCELADA': 'cancelada',
            'AGENDADA': 'reaberta como agendada',
        }
        messages.success(
            request,
            f'Consulta de {consulta.paciente.username} ({consulta.data:%d/%m/%Y} às {consulta.horario:%H:%M}) marcada como {labels[novo_status]}.',
        )

    return redirect('painel_medico')


def monitoramento_admin(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login como administrador para acessar o monitoramento.')
        return redirect(f"{reverse('login')}?next={request.path}")

    if not request.user.is_staff:
        messages.error(request, 'Acesso restrito aos administradores do Instituto Vitta.')
        return redirect('home')

    hoje = timezone.localdate()
    total_usuarios = User.objects.count()
    total_profissionais = Profissional.objects.count()
    profissionais_com_conta = Profissional.objects.filter(usuario__isnull=False).count()
    total_pacientes = User.objects.filter(perfil_profissional__isnull=True, is_staff=False).count()

    todas_consultas = Consulta.objects.select_related(
        'paciente', 'profissional', 'profissional__especialidade'
    )

    ultimos_usuarios = User.objects.select_related('perfil_profissional').order_by('-date_joined')[:10]
    ultimos_profissionais = Profissional.objects.select_related('especialidade', 'usuario').order_by('-id')[:10]
    ultimas_consultas = todas_consultas.order_by('-criado_em', '-id')[:15]

    ranking_profissionais = Profissional.objects.select_related('especialidade').annotate(
        total_atendimentos=Count('consultas'),
        atendimentos_ativos=Count('consultas', filter=Q(consultas__status__in=['AGENDADA', 'CONCLUIDA'])),
    ).order_by('-total_atendimentos', 'nome')

    contexto = {
        'hoje': hoje,
        'total_usuarios': total_usuarios,
        'total_pacientes': total_pacientes,
        'total_profissionais': total_profissionais,
        'profissionais_com_conta': profissionais_com_conta,
        'total_especialidades': Especialidade.objects.count(),
        'total_consultas': todas_consultas.count(),
        'consultas_agendadas': todas_consultas.filter(status='AGENDADA').count(),
        'consultas_concluidas': todas_consultas.filter(status='CONCLUIDA').count(),
        'consultas_canceladas': todas_consultas.filter(status='CANCELADA').count(),
        'ultimos_usuarios': ultimos_usuarios,
        'ultimos_profissionais': ultimos_profissionais,
        'ultimas_consultas': ultimas_consultas,
        'ranking_profissionais': ranking_profissionais,
    }
    return render(request, 'agendamento/monitoramento_admin.html', contexto)


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Você foi desconectado com sucesso.')
    return redirect('home')



def agendar(request, profissional_id):
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login ou cadastre-se para agendar uma consulta.')
        return redirect(f"{reverse('login')}?next={request.path}")

    try:
        profissional = Profissional.objects.select_related('especialidade').get(id=profissional_id, ativo=True)
    except Profissional.DoesNotExist:
        messages.error(request, 'Profissional não encontrado ou indisponível no momento.')
        return redirect('home')

    perfil_logado = _obter_perfil_profissional(request.user)
    if perfil_logado and perfil_logado.id == profissional.id:
        messages.warning(request, 'Você não pode agendar uma consulta consigo mesmo.')
        return redirect('painel_medico')

    agora_local = timezone.localtime()
    hoje = agora_local.date()
    data_padrao = _proxima_data_util(hoje)

    if request.method == 'POST':
        data_str = (request.POST.get('data_consulta') or request.POST.get('data') or '').strip()
        horario_str = (request.POST.get('horario_consulta') or request.POST.get('horario') or '').strip()
        observacoes = (request.POST.get('observacoes') or '').strip()

        def _render_erro(msg, data_ref=data_padrao):
            messages.error(request, msg)
            horarios, aviso = _gerar_grade_horarios(profissional, data_ref)
            return render(request, 'agendamento/agendar_consulta.html', {
                'profissional': profissional,
                'medico': profissional,
                'horarios': horarios,
                'aviso_horarios': aviso,
                'data_minima': hoje.isoformat(),
                'data_selecionada': data_ref.isoformat(),
                'observacoes_salvas': observacoes,
            })

        if not data_str or not horario_str:
            return _render_erro('Selecione uma data e um horário disponível antes de confirmar.')

        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return _render_erro('Data informada inválida.')

        if data_obj < hoje:
            return _render_erro('Não é possível agendar consultas em datas passadas.', data_padrao)

        if data_obj.weekday() == 6:
            return _render_erro('Não realizamos atendimentos aos domingos. Escolha outra data.', data_obj)

        if horario_str not in HORARIOS_ATENDIMENTO:
            return _render_erro('Horário selecionado inválido.', data_obj)

        horario_obj = datetime.strptime(horario_str, '%H:%M').time()

        if data_obj == hoje and horario_obj <= agora_local.time():
            return _render_erro('Este horário já passou hoje. Escolha outro horário.', data_obj)

        conflito_medico = Consulta.objects.filter(
            profissional=profissional,
            data=data_obj,
            horario=horario_obj,
        ).exclude(status='CANCELADA').exists()

        if conflito_medico:
            return _render_erro('Este horário acabou de ser reservado. Escolha outro horário disponível.', data_obj)

        conflito_paciente = Consulta.objects.filter(
            paciente=request.user,
            data=data_obj,
            horario=horario_obj,
            status='AGENDADA',
        ).exists()

        if conflito_paciente:
            return _render_erro('Você já possui uma consulta agendada neste mesmo dia e horário.', data_obj)

        try:
            with transaction.atomic():
                Consulta.objects.create(
                    paciente=request.user,
                    profissional=profissional,
                    data=data_obj,
                    horario=horario_obj,
                    observacoes=observacoes,
                )
        except IntegrityError:
            return _render_erro(
                'Este horário acabou de ser reservado. Atualize a agenda e escolha outro horário.',
                data_obj,
            )

        messages.success(
            request,
            f'Consulta agendada com {profissional.nome_exibicao} em {data_obj:%d/%m/%Y} às {horario_str}!',
        )
        return redirect('minhas_consultas')

    # GET
    data_query = request.GET.get('data', '').strip()
    data_selecionada = data_padrao
    if data_query:
        try:
            data_parsed = datetime.strptime(data_query, '%Y-%m-%d').date()
            if data_parsed >= hoje:
                data_selecionada = data_parsed
        except ValueError:
            pass

    horarios, aviso = _gerar_grade_horarios(profissional, data_selecionada)

    contexto = {
        'profissional': profissional,
        'medico': profissional,
        'horarios': horarios,
        'aviso_horarios': aviso,
        'data_minima': hoje.isoformat(),
        'data_selecionada': data_selecionada.isoformat(),
    }
    return render(request, 'agendamento/agendar_consulta.html', contexto)


def api_horarios(request, profissional_id):
    if not request.user.is_authenticated:
        return JsonResponse({'erro': 'Autenticação necessária.'}, status=401)

    profissional = get_object_or_404(Profissional, id=profissional_id, ativo=True)
    data_str = (request.GET.get('data') or '').strip()

    try:
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'horarios': [], 'mensagem': 'Data inválida.'}, status=400)

    horarios, aviso = _gerar_grade_horarios(profissional, data_obj)
    return JsonResponse({
        'horarios': horarios,
        'mensagem': aviso,
    })
