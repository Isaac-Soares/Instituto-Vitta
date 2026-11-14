# Instituto Vitta — Preparação para deploy

Este projeto usa Django, SQLite no desenvolvimento local e PostgreSQL quando `DATABASE_URL` é definida. O servidor de produção recomendado nesta primeira etapa é o Render.

## Funcionalidades existentes

- Cadastro e login de pacientes.
- Cadastro de profissionais com publicação imediata do perfil na vitrine.
- Busca de profissionais e filtro por especialidade.
- Painel do profissional para acompanhar e atualizar consultas.
- Agendamento com bloqueio de horários ocupados e restrições de data.
- Painel de monitoramento restrito a usuários `is_staff`.
- Recuperação de senha por link temporário enviado por e-mail.
- Restrições no banco para impedir duas reservas ativas no mesmo horário do profissional e duas consultas agendadas do mesmo paciente no mesmo horário.

> **Importante:** a publicação imediata significa que o cadastro é exibido assim que concluído. O sistema não consulta automaticamente conselhos profissionais para validar CRM/CRP/CRN. Para uso real, implemente um processo de verificação documental e revisão de perfis, além de termos de uso e política de privacidade.

## Executar localmente (Windows / PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. Em desenvolvimento, o e-mail de recuperação é exibido no terminal do servidor (console email backend).

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---:|---|
| `SECRET_KEY` | Sim em produção | Chave secreta longa e aleatória. Não coloque no Git. |
| `DEBUG` | Sim em produção | Use `False`. |
| `ALLOWED_HOSTS` | Recomendado | Domínios permitidos separados por vírgula. |
| `CSRF_TRUSTED_ORIGINS` | Se necessário | Origens completas com `https://`, separadas por vírgula. |
| `DATABASE_URL` | Sim em produção | URL de conexão PostgreSQL. |
| `EMAIL_HOST` | Sim para recuperação de senha em produção | Servidor SMTP do provedor de e-mail. |
| `EMAIL_PORT` | Não | Porta SMTP; padrão `587`. |
| `EMAIL_HOST_USER` | Sim para SMTP autenticado | Usuário SMTP. |
| `EMAIL_HOST_PASSWORD` | Sim para SMTP autenticado | Senha ou token SMTP. |
| `EMAIL_USE_TLS` | Não | Padrão `True`. |
| `DEFAULT_FROM_EMAIL` | Recomendado | Remetente dos e-mails. |
| `SECURE_SSL_REDIRECT` | Não | Padrão `True` quando `DEBUG=False`. |

Nunca versione `.env`, senhas, tokens, dumps de banco ou dados reais de pacientes. O arquivo `db.sqlite3` que acompanhava a versão recebida foi intencionalmente excluído do pacote atualizado: ele continha contas e registros locais. O banco novo é criado pelas migrações; cadastre os profissionais e o administrador no ambiente de destino.

## Deploy no Render

1. Envie o conteúdo desta pasta para um repositório GitHub privado ou público, sem arquivos `.env` ou bancos locais.
2. Crie um banco PostgreSQL e um Web Service no Render.
3. Configure o Build Command como `./build.sh`.
4. Configure o Start Command como `gunicorn instituto_vitta.wsgi:application`.
5. Configure `DATABASE_URL` com a URL interna/privada do banco PostgreSQL fornecida pelo provedor, quando disponível.
6. Defina `DEBUG=False` e gere uma `SECRET_KEY` segura no painel de variáveis do serviço.
7. Defina `ALLOWED_HOSTS` com o domínio do serviço (ou use `RENDER_EXTERNAL_HOSTNAME`, que o Django lê automaticamente).
8. Configure SMTP para que a recuperação de senha funcione fora do ambiente local.
9. Após o primeiro deploy, crie o administrador pelo Shell do serviço: `python manage.py createsuperuser`.
10. Teste cadastro de paciente, cadastro profissional, login, recuperação de senha, agendamento, cancelamento e painel administrativo.

O script de build executa `collectstatic` e as migrações. Ele não cria contas administrativas nem profissionais fictícios automaticamente.

## Cuidados antes de usar com pacientes reais

- Configure SMTP e teste a entrega dos e-mails.
- Verifique identidade e registro profissional antes de divulgar o serviço como plataforma clínica.
- Publique política de privacidade, termos de uso e canal para solicitações LGPD.
- Restrinja o acesso a dados de consultas; evite registrar informações clínicas desnecessárias no campo de observações.
- Configure backups, monitoramento, logs sem dados sensíveis e processo de resposta a incidentes.
- Faça revisão de segurança e testes de carga antes de abrir ao público.
- Não use dados reais de pacientes em demonstrações, testes ou no portfólio.

Este repositório é uma base de portfólio preparada tecnicamente para deploy, não uma certificação de conformidade legal ou clínica.
