# bina/management/commands/otomatik_aidat_olustur.py
from django.core.management.base import BaseCommand
from datetime import date
from bina.models import Daire, Aidat, SiteAyarlari

class Command(BaseCommand):
    help = 'Otomatik aidat oluşturur'

    def handle(self, *args, **kwargs):
        bugun = date.today()
        ay = bugun.month
        yil = bugun.year
        
        site_ayar = SiteAyarlari.objects.first()
        if not site_ayar or not site_ayar.sabit_aidat_aktif_mi:
            return
        
        if bugun.day != site_ayar.sabit_aidat_kesim_gunu:
            return
        
        if Aidat.objects.filter(ay=ay, yil=yil, aidat_tipi='sabit').exists():
            return
        
        for daire in Daire.objects.all():
            Aidat.objects.create(
                daire=daire,
                ay=ay,
                yil=yil,
                aidat_tipi='sabit',
                tutar=site_ayar.sabit_aidat_miktari,
                aciklama=f"{ay}/{yil} Sabit Aidat"
            )
        
        self.stdout.write(f'✅ {ay}/{yil} aidatları oluşturuldu')