# bina/context_processors.py - Güncelleyin

from .models import Site

def site_selector(request):
    """Site seçici context processor - Tüm sayfalar için"""
    sites = Site.objects.filter(aktif=True)
    aktif_site_id = None
    aktif_site = None
    
    # Admin paneli için
    if request.path.startswith('/admin/'):
        aktif_site_id = request.session.get('aktif_site_id')
        if aktif_site_id:
            try:
                aktif_site = Site.objects.get(id=aktif_site_id, aktif=True)
            except Site.DoesNotExist:
                aktif_site = Site.objects.filter(aktif=True).first()
        else:
            aktif_site = Site.objects.filter(aktif=True).first()
    
    # Portal için
    elif request.path.startswith('/portal/'):
        aktif_site_id = request.session.get('portal_site_id')
        if aktif_site_id:
            try:
                aktif_site = Site.objects.get(id=aktif_site_id, aktif=True)
            except Site.DoesNotExist:
                aktif_site = Site.objects.filter(aktif=True).first()
        else:
            aktif_site = Site.objects.filter(aktif=True).first()
    
    # Ana sayfa ve diğer sayfalar için
    else:
        aktif_site_id = request.session.get('aktif_site_id') or request.session.get('portal_site_id')
        if aktif_site_id:
            try:
                aktif_site = Site.objects.get(id=aktif_site_id, aktif=True)
            except Site.DoesNotExist:
                aktif_site = Site.objects.filter(aktif=True).first()
        else:
            aktif_site = Site.objects.filter(aktif=True).first()
    
    return {
        'sites': sites,
        'aktif_site_id': aktif_site_id,
        'aktif_site': aktif_site,  # YENİ: Aktif site objesi
    }