from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


class Especialidade(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Especialidade'
        verbose_name_plural = 'Especialidades'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Profissional(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='perfil_profissional',
        verbose_name='Conta de usuário',
    )
    nome = models.CharField(max_length=100, verbose_name='Nome')
    registro = models.CharField(max_length=50, verbose_name='Registro profissional')
    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.CASCADE,
        verbose_name='Especialidade',
    )
    bio = models.TextField(
        blank=True,
        default='',
        verbose_name='Apresentação / Bio',
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo na vitrine',
    )

    class Meta:
        verbose_name = 'Profissional'
        verbose_name_plural = 'Profissionais'
        ordering = ['nome']

    @property
    def nome_exibicao(self):
        nome_limpo = self.nome.strip()
        prefixos = ('dr.', 'dra.', 'dr ', 'dra ')
        if nome_limpo.lower().startswith(prefixos):
            return nome_limpo
        return f'Dr(a). {nome_limpo}'

    @property
    def iniciais(self):
        partes = [
            p for p in self.nome.replace('.', '').split()
            if p.lower() not in ('dr', 'dra', 'de', 'da', 'do', 'dos', 'das')
        ]
        if not partes:
            return self.nome[:1].upper()
        if len(partes) == 1:
            return partes[0][:2].upper()
        return f'{partes[0][0]}{partes[-1][0]}'.upper()

    def __str__(self):
        return f'{self.nome_exibicao} ({self.especialidade.nome})'


class Consulta(models.Model):
    STATUS_CHOICES = (
        ('AGENDADA', 'Agendada'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    )

    paciente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consultas',
        verbose_name='Paciente',
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='consultas',
        verbose_name='Profissional',
    )
    data = models.DateField(verbose_name='Data')
    horario = models.TimeField(verbose_name='Horário')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='AGENDADA',
        verbose_name='Status',
    )
    observacoes = models.TextField(
        blank=True,
        default='',
        verbose_name='Observações',
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em',
    )

    class Meta:
        verbose_name = 'Consulta'
        verbose_name_plural = 'Consultas'
        ordering = ['-data', '-horario']
        constraints = [
            models.UniqueConstraint(
                fields=['profissional', 'data', 'horario'],
                condition=~Q(status='CANCELADA'),
                name='unique_profissional_horario_ativo',
            ),
            models.UniqueConstraint(
                fields=['paciente', 'data', 'horario'],
                condition=Q(status='AGENDADA'),
                name='unique_paciente_horario_agendado',
            ),
        ]

    def __str__(self):
        return f'Consulta de {self.paciente.username} com {self.profissional.nome_exibicao} em {self.data:%d/%m/%Y} às {self.horario:%H:%M}'
