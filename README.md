# Instituto Vitta — Sistema de Agendamento de Consultas

🚀 **Teste a aplicação online:** [Acesse o Instituto Vitta no Render](https://instituto-vitta.onrender.com) *(ou substitua pelo seu link de deploy)*

Aplicação web desenvolvida em **Django** para agendamento de consultas médicas e acompanhamento de atendimentos do **Instituto Vitta**.

## Funcionalidades Implementadas

- **Página Inicial (`/`):** Apresentação institucional, busca por profissional/especialidade/registro e filtros interativos por especialidade.
- **Especialidades (`/especialidades/`):** Catálogo completo das especialidades cadastradas com descrição, quantidade de profissionais e atalho direto para agendamento.
- **Agendamento Inteligente (`/agendar/<profissional_id>/` + `/api/horarios/<profissional_id>/`):**
  - Grade interativa de horários com atualização dinâmica via AJAX ao trocar a data.
  - Bloqueio automático de datas passadas, domingos, horários encerrados no dia e horários já reservados.
  - Campo opcional de observações para o atendimento.
- **Minhas Consultas (`/minhas-consultas/`):** Painel do paciente com indicadores, separação entre próximas consultas e histórico, e cancelamento seguro com confirmação.
- **Autenticação (`/login/`, `/logout/`, `/recuperar-senha/`):** login com redirecionamento inteligente, cadastro com validação e recuperação de senha por link temporário enviado ao e-mail.
- **Cadastro profissional:** médicos e especialistas podem criar conta e ter o perfil publicado imediatamente; o registro informado não é verificado automaticamente.
- **Proteção de agenda:** o banco impede reservas ativas duplicadas para o mesmo profissional e consultas agendadas duplicadas do mesmo paciente no mesmo horário.
- **Painel Administrativo (`/admin/`):** Gestão de especialidades, profissionais e consultas com filtros, busca e edição rápida de status.

## Deploy

Consulte [README_DEPLOY.md](README_DEPLOY.md) para configurar PostgreSQL, e-mail SMTP e publicar no Render.

## Como Executar

1. Ative o ambiente virtual (ou crie um novo):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```
2. Instale as dependências (caso ainda não estejam no seu `venv`):
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie o servidor de desenvolvimento:
   ```bash
   python manage.py runserver
   ```
4. Acesse no navegador: `http://127.0.0.1:8000/` (ou `http://127.0.0.1:8000/admin/`).
