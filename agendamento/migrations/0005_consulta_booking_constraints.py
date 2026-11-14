from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ('agendamento', '0004_profissional_ativo_profissional_bio_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='consulta',
            constraint=models.UniqueConstraint(
                fields=('profissional', 'data', 'horario'),
                condition=~Q(status='CANCELADA'),
                name='unique_profissional_horario_ativo',
            ),
        ),
        migrations.AddConstraint(
            model_name='consulta',
            constraint=models.UniqueConstraint(
                fields=('paciente', 'data', 'horario'),
                condition=Q(status='AGENDADA'),
                name='unique_paciente_horario_agendado',
            ),
        ),
    ]
