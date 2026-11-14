from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.core import mail
from django.urls import reverse

from .models import Consulta, Especialidade, Profissional


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class InstitutoVittaTests(TestCase):
    def setUp(self):
        self.esp_psico = Especialidade.objects.create(
            nome='Psicologia',
            descricao='Saúde mental e bem-estar.',
        )
        self.esp_endoc = Especialidade.objects.create(
            nome='Endocrinologia',
            descricao='Saúde hormonal e metabolismo.',
        )
        self.prof1 = Profissional.objects.create(
            nome='Dra. Júlia Monique',
            registro='CRP-DF 34567',
            especialidade=self.esp_psico,
        )
        self.prof2 = Profissional.objects.create(
            nome='Rafael Costa',
            registro='CRM-DF 12345',
            especialidade=self.esp_endoc,
        )
        self.user = User.objects.create_user(
            username='paciente1',
            email='paciente1@vitta.com',
            password='Password123',
        )

    def _proxima_segunda(self):
        hoje = date.today()
        dias = (7 - hoje.weekday()) % 7
        return hoje + timedelta(days=dias or 7)

    def test_nome_exibicao_e_iniciais(self):
        self.assertEqual(self.prof1.nome_exibicao, 'Dra. Júlia Monique')
        self.assertEqual(self.prof1.iniciais, 'JM')
        self.assertEqual(self.prof2.nome_exibicao, 'Dr(a). Rafael Costa')
        self.assertEqual(self.prof2.iniciais, 'RC')

    def test_home_e_filtros(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Dra. Júlia Monique')
        self.assertContains(resp, 'Dr(a). Rafael Costa')

        resp_filtro = self.client.get(reverse('home'), {'especialidade': self.esp_psico.id})
        self.assertContains(resp_filtro, 'Dra. Júlia Monique')
        self.assertNotContains(resp_filtro, 'Rafael Costa')

    def test_pagina_especialidades(self):
        resp = self.client.get(reverse('especialidades'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Psicologia')
        self.assertContains(resp, 'Endocrinologia')

    def test_cadastro_duplicado_e_login(self):
        resp_dup = self.client.post(reverse('login'), {
            'username': 'paciente1',
            'email': 'outro@vitta.com',
            'password1': 'SenhaForte1',
            'password2': 'SenhaForte1',
        })
        self.assertEqual(resp_dup.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

        resp_ok = self.client.post(reverse('login'), {
            'username': 'novo_paciente',
            'email': 'novo@vitta.com',
            'password1': 'SenhaForte1',
            'password2': 'SenhaForte1',
        })
        self.assertRedirects(resp_ok, reverse('home'))
        self.assertTrue(User.objects.filter(username='novo_paciente').exists())

    def test_agendamento_e_bloqueio_conflito(self):
        self.client.login(username='paciente1', password='Password123')
        data_futura = self._proxima_segunda()

        # Primeiro agendamento deve funcionar
        resp = self.client.post(
            reverse('agendar_consulta', args=[self.prof1.id]),
            {
                'data_consulta': data_futura.isoformat(),
                'horario_consulta': '10:00',
                'observacoes': 'Primeira consulta',
            },
        )
        self.assertRedirects(resp, reverse('minhas_consultas'))
        self.assertEqual(Consulta.objects.count(), 1)

        # Segundo agendamento no mesmo horário deve ser bloqueado
        resp_conflito = self.client.post(
            reverse('agendar_consulta', args=[self.prof1.id]),
            {
                'data_consulta': data_futura.isoformat(),
                'horario_consulta': '10:00',
            },
        )
        self.assertEqual(resp_conflito.status_code, 200)
        self.assertEqual(Consulta.objects.count(), 1)

        # API de horários deve marcar 10:00 como ocupado
        resp_api = self.client.get(
            reverse('api_horarios', args=[self.prof1.id]),
            {'data': data_futura.isoformat()},
        )
        self.assertEqual(resp_api.status_code, 200)
        horarios = {h['hora']: h['ocupado'] for h in resp_api.json()['horarios']}
        self.assertTrue(horarios['10:00'])
        self.assertFalse(horarios['11:00'])

    def test_minhas_consultas_e_cancelamento(self):
        self.client.login(username='paciente1', password='Password123')
        data_futura = self._proxima_segunda()
        consulta = Consulta.objects.create(
            paciente=self.user,
            profissional=self.prof1,
            data=data_futura,
            horario=time(14, 0),
        )

        resp_lista = self.client.get(reverse('minhas_consultas'))
        self.assertEqual(resp_lista.status_code, 200)
        self.assertContains(resp_lista, 'Dra. Júlia Monique')

        resp_cancelar = self.client.post(reverse('cancelar_consulta', args=[consulta.id]))
        self.assertRedirects(resp_cancelar, reverse('minhas_consultas'))
        consulta.refresh_from_db()
        self.assertEqual(consulta.status, 'CANCELADA')
    def test_cadastro_profissional_publica_perfil_imediatamente(self):
        resposta = self.client.post(reverse('cadastro_profissional'), {
            'nome_profissional': 'Dra. Marina Silva',
            'registro': 'CRM-DF 99887',
            'especialidade': str(self.esp_psico.id),
            'bio': 'Atendimento clínico.',
            'username': 'dra_marina',
            'email': 'marina@vitta.com',
            'password1': 'SenhaForte123',
            'password2': 'SenhaForte123',
        })
        self.assertRedirects(resposta, reverse('painel_medico'))
        profissional = Profissional.objects.get(registro='CRM-DF 99887')
        self.assertTrue(profissional.ativo)
        self.assertEqual(profissional.usuario.username, 'dra_marina')
        resposta_home = self.client.get(reverse('home'))
        self.assertContains(resposta_home, 'Dra. Marina Silva')

    def test_banco_impede_duas_consultas_ativas_no_mesmo_horario(self):
        data_futura = self._proxima_segunda()
        Consulta.objects.create(
            paciente=self.user, profissional=self.prof1, data=data_futura, horario=time(10, 0)
        )
        outro_paciente = User.objects.create_user(
            username='paciente2', email='paciente2@vitta.com', password='Password123'
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Consulta.objects.create(
                    paciente=outro_paciente, profissional=self.prof1,
                    data=data_futura, horario=time(10, 0),
                )

    def test_recuperacao_nao_altera_senha_sem_confirmacao_por_email(self):
        senha_anterior = self.user.password
        resposta = self.client.post(reverse('recuperar_senha'), {
            'email': 'paciente1@vitta.com',
        })

        # A solicitação válida redireciona para a página de confirmação de envio.
        self.assertRedirects(resposta, reverse('recuperar_senha_enviado'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['paciente1@vitta.com'])
        self.assertIn('/recuperar-senha/confirmar/', mail.outbox[0].body)

        # A senha só pode mudar depois que o usuário acessa o link/token do e-mail.
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, senha_anterior)

    def test_logout_nao_aceita_get_para_encerrar_sessao(self):
        self.client.login(username='paciente1', password='Password123')
        self.client.get(reverse('logout'))
        self.assertTrue('_auth_user_id' in self.client.session)
        self.client.post(reverse('logout'))
        self.assertFalse('_auth_user_id' in self.client.session)

