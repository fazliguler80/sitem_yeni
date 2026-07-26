# portal/views.py veya ana views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, login_not_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from bina.models import DaireKullanici, Depozito, DepozitoHareket, Site
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView

@staff_member_required
def site_degistir(request, site_id):
    """Admin paneli için site seçici - session'a kaydeder"""
    try:
        site = Site.objects.get(id=site_id, aktif=True)
        request.session['aktif_site_id'] = site.id
        request.session['aktif_site_adi'] = site.adi
        print(f"✅ SESSION KAYDEDİLDİ: Site ID={site.id}, Adi={site.adi}")
    except Site.DoesNotExist:
        print(f"❌ Site bulunamadı: ID={site_id}")
        pass
    
    # Yönlendirme yapılacak adresi al (next parametresi)
    next_url = request.GET.get('next', '/admin/')
    return redirect(next_url)


class AdminLoginView(LoginView):
    template_name = 'admin/login.html'
    
    def form_valid(self, form):
        # Kullanıcıyı oturum açtır
        response = super().form_valid(form)
        
        # Her durumda admin paneline yönlendir
        return redirect('/admin/')
    
    def get_success_url(self):
        # Her durumda admin paneline yönlendir
        return '/admin/'

@login_not_required
def portal_site_degistir(request, site_id):
    """Portal için site seçici"""
    from bina.models import Site
    try:
        site = Site.objects.get(id=site_id, aktif=True)
        request.session['portal_site_id'] = site.id
        request.session['portal_site_adi'] = site.adi
    except Site.DoesNotExist:
        pass
    next_url = request.GET.get('next', '/portal/login/')
    return redirect(next_url)

@login_required(login_url='/portal/login/')
def portal_depozito_gecmisi(request):
    """Portal kullanıcısının depozito geçmişini göster (Ek depozito borcu dahil)"""
    from decimal import Decimal
    
    # Giriş yapan kullanıcının daire bilgisini bul
    try:
        daire_kullanici = DaireKullanici.objects.get(kullanici=request.user)
        daire = daire_kullanici.daire
    except DaireKullanici.DoesNotExist:
        messages.error(request, "Daire bilginize ulaşılamadı.")
        return render(request, 'portal/depozito_gecmisi.html', {'error': True})
    
    # Dairenin aktif depozitosunu bul
    depozito = Depozito.objects.filter(daire=daire, durum='alindi').first()
    
    if not depozito:
        context = {
            'daire': daire,
            'depozito_var': False,
            'gecmis_hareketler': [],
            'toplam_depozito': 0,
            'guncel_bakiye': 0,
            'ek_depozito_borcu': 0,
        }
        return render(request, 'portal/depozito_gecmisi.html', context)
    
    # ========== EK DEPOZİTO BORCU ==========
    ek_depozito_borcu = Decimal('0.00')
    if depozito.ek_depozito_tutari and not depozito.ek_depozito_odendi_mi:
        ek_depozito_borcu = Decimal(str(depozito.ek_depozito_tutari))
    
    # ========== GUNCEL BAKIYE ==========
    guncel_bakiye = Decimal(str(depozito.tutar))
    
    # Ödenmiş ek depozitoyu ekle
    if depozito.ek_depozito_odendi_mi and depozito.ek_depozito_tutari:
        guncel_bakiye += Decimal(str(depozito.ek_depozito_tutari))
    
    # İade edilen tutarı düş
    if depozito.iade_tutari:
        guncel_bakiye -= Decimal(str(depozito.iade_tutari))
    
    # Depozito hareketlerini al
    hareketler = depozito.hareketler.all().order_by('tarih', 'id')
    
    # Her harekete bakiye bilgisi ekle
    bakiye_float = float(guncel_bakiye)  # Başlangıç bakiyesi
    hareket_listesi = []
    
    # Önce hareketleri ters sırada göster (en yeni en üstte)
    for hareket in hareketler.order_by('-tarih', '-id'):
        if hareket.hareket_tipi == 'ekleme':
            islem_icon = '➕'
            renk = 'success'
            tutar_goster = f"+ {float(hareket.tutar):.2f} TL"
        elif hareket.hareket_tipi == 'ek_depozito':
            islem_icon = '💰'
            renk = 'info'
            tutar_goster = f"+ {float(hareket.tutar):.2f} TL"
        elif hareket.hareket_tipi == 'cikarma':
            islem_icon = '➖'
            renk = 'danger'
            tutar_goster = f"- {float(hareket.tutar):.2f} TL"
        else:  # iade
            islem_icon = '↩️'
            renk = 'warning'
            tutar_goster = f"- {float(hareket.tutar):.2f} TL"
        
        hareket_listesi.append({
            'tarih': hareket.tarih,
            'islem_tipi': hareket.get_hareket_tipi_display(),
            'islem_icon': islem_icon,
            'renk': renk,
            'tutar': float(hareket.tutar),
            'tutar_goster': tutar_goster,
            'aciklama': hareket.aciklama,
            'gider': hareket.gider,
            'aidat': hareket.aidat,
        })
    
    # Toplam depozito (ana depozito + ödenen ek depozito)
    toplam_depozito = float(depozito.tutar)
    if depozito.ek_depozito_odendi_mi and depozito.ek_depozito_tutari:
        toplam_depozito += float(depozito.ek_depozito_tutari)
    
    context = {
        'daire': daire,
        'depozito': depozito,
        'depozito_var': True,
        'toplam_depozito': toplam_depozito,
        'guncel_bakiye': float(guncel_bakiye),
        'ek_depozito_borcu': float(ek_depozito_borcu),
        'gecmis_hareketler': hareket_listesi,
    }
    
    return render(request, 'portal/depozito_gecmisi.html', context)


@login_required(login_url='/portal/login/')
def portal_depozito_detay(request, depozito_id):
    """Tek bir depozitonun detaylı geçmişi (Ek depozito borcu dahil)"""
    from decimal import Decimal
    
    depozito = get_object_or_404(Depozito, id=depozito_id)
    
    # Kullanıcının bu depozitoya erişim yetkisi var mı kontrol et
    try:
        daire_kullanici = DaireKullanici.objects.get(kullanici=request.user)
        if depozito.daire != daire_kullanici.daire:
            messages.error(request, "Bu depozito bilgisine erişim yetkiniz yok.")
            return redirect('portal_depozito_gecmisi')
    except DaireKullanici.DoesNotExist:
        messages.error(request, "Daire bilginize ulaşılamadı.")
        return redirect('portal_depozito_gecmisi')
    
    # ========== EK DEPOZİTO BORCU ==========
    ek_depozito_borcu = Decimal('0.00')
    if depozito.ek_depozito_tutari and not depozito.ek_depozito_odendi_mi:
        ek_depozito_borcu = Decimal(str(depozito.ek_depozito_tutari))
    
    # ========== GUNCEL BAKIYE ==========
    guncel_bakiye = Decimal(str(depozito.tutar))
    
    if depozito.ek_depozito_odendi_mi and depozito.ek_depozito_tutari:
        guncel_bakiye += Decimal(str(depozito.ek_depozito_tutari))
    
    if depozito.iade_tutari:
        guncel_bakiye -= Decimal(str(depozito.iade_tutari))
    
    # Hareketler
    hareketler = depozito.hareketler.all().order_by('-tarih', '-id')
    
    # Bakiye hesaplama (en eski -> en yeni)
    bakiye_hesap = Decimal('0.00')
    hareket_listesi = []
    
    # Önce eski hareketleri sıralı al
    eski_hareketler = depozito.hareketler.all().order_by('tarih', 'id')
    for h in eski_hareketler:
        if h.hareket_tipi in ['ekleme', 'ek_depozito']:
            bakiye_hesap += Decimal(str(h.tutar))
        elif h.hareket_tipi in ['cikarma', 'iade']:
            bakiye_hesap -= Decimal(str(h.tutar))
        
        # Her harekete bakiye ekle
        h.bakiye = float(bakiye_hesap)
    
    # Sonra detaylı liste oluştur (en yeni en üstte)
    for h in hareketler:
        if h.hareket_tipi == 'ekleme':
            islem_icon = '➕'
            renk = 'success'
            tip_label = 'Depozitoya Eklendi'
        elif h.hareket_tipi == 'ek_depozito':
            islem_icon = '💰'
            renk = 'info'
            tip_label = 'Ek Depozito Eklendi'
        elif h.hareket_tipi == 'cikarma':
            islem_icon = '➖'
            renk = 'danger'
            tip_label = 'Depozitodan Düşüldü'
        else:
            islem_icon = '↩️'
            renk = 'warning'
            tip_label = 'İade Edildi'
        
        hareket_listesi.append({
            'id': h.id,
            'tarih': h.tarih,
            'islem_tipi': h.get_hareket_tipi_display(),
            'islem_icon': islem_icon,
            'renk': renk,
            'tip_label': tip_label,
            'tutar': float(h.tutar),
            'bakiye': float(bakiye_hesap),
            'aciklama': h.aciklama,
            'gider': h.gider,
            'aidat': h.aidat,
        })
    
    # Toplam depozito
    toplam_depozito = float(depozito.tutar)
    if depozito.ek_depozito_odendi_mi and depozito.ek_depozito_tutari:
        toplam_depozito += float(depozito.ek_depozito_tutari)
    
    context = {
        'depozito': depozito,
        'daire': depozito.daire,
        'toplam_depozito': toplam_depozito,
        'guncel_bakiye': float(guncel_bakiye),
        'ek_depozito_borcu': float(ek_depozito_borcu),
        'hareketler': hareket_listesi,
    }
    
    return render(request, 'portal/depozito_detay.html', context)

def home_page(request):
    """Ana sayfa görünümü"""
    return render(request, 'home.html')
