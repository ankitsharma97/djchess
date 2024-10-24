# Generated by Django 4.2.16 on 2024-10-20 05:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0004_game_winner'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='result',
            field=models.CharField(blank=True, choices=[('win', 'Win'), ('loss', 'Loss'), ('draw', 'Draw'), ('stalemate', 'Stalemate')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='player2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='games_as_player2', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='game',
            name='winner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='games_won', to=settings.AUTH_USER_MODEL),
        ),
    ]
