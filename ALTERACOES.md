# Alterações desta versão

## Funcionalidades e segurança

- Mantido o cadastro de profissionais com `ativo=True`, portanto o perfil é publicado imediatamente após o cadastro.
- Acrescentado aviso na tela de cadastro: CRM/CRP/CRN é autodeclarado e não passa por validação automática.
- Substituída a recuperação de senha baseada apenas em usuário + e-mail por fluxo nativo do Django com link temporário enviado por e-mail.
- Logout alterado para requisição POST com proteção CSRF.
- Criadas restrições únicas condicionais para evitar colisões de horários de profissionais e consultas agendadas duplicadas do mesmo paciente.
- Tratado o conflito de integridade em reservas concorrentes e na reabertura de consultas.
- API de horários agora só consulta profissionais ativos.

## Deploy

- `SECRET_KEY` passa a ser obrigatória quando `DEBUG=False`; removido o segredo fixo de produção.
- `ALLOWED_HOSTS` deixa de aceitar `*` por padrão.
- Configurações de HTTPS, cookies seguros, HSTS e proxy reverso preparadas para produção.
- PostgreSQL configurado por `DATABASE_URL`; erro explícito caso falte `dj-database-url`.
- E-mail de console no desenvolvimento e SMTP configurável por variáveis de ambiente em produção.
- Corrigido `build.sh`: removida chamada para `popular_vitta`, comando que não existia; adicionados check, collectstatic e migrate.
- Documentação de instalação, variáveis, Render, SMTP e cuidados com dados pessoais atualizada.
- Adicionado `.env.example`.

## Dados locais

O banco SQLite que veio no ZIP original não foi incluído nesta entrega porque continha seis contas, três perfis profissionais e uma consulta local. O banco do ambiente de destino deve ser criado com `python manage.py migrate`. Nenhuma conta ou consulta local foi copiada para a nova versão.

## Validação

- Compilação sintática dos arquivos Python: aprovada (`compileall` e `ast.parse`).
- Testes automatizados: não foi possível executá-los neste ambiente porque Django não está instalado e a conexão de rede para instalar dependências está indisponível. Os testes novos foram adicionados ao projeto para execução local.
