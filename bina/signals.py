# bina/signals.py
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver
from .models import Gider, Aidat, DepozitoHareket, Depozito, BankaHareket, Banka
from decimal import Decimal
from datetime import date


@receiver(pre_delete, sender=Gider)
def gider_silinmeden_once_aidatlari_sil(sender, instance, **kwargs):
    """Gider silinmeden önce bağlı aidatları ve depozito hareketlerini sil"""
    print(f"\n=== Gider siliniyor: {instance} ===")
    
    aidatlar = Aidat.objects.filter(gider=instance)
    aidat_sayisi = aidatlar.count()
    
    if aidat_sayisi > 0:
        print(f"  {aidat_sayisi} adet aidat siliniyor...")
        for aidat in aidatlar:
            print(f"    - {aidat.daire} - {aidat.ay}/{aidat.yil} - {aidat.tutar} TL")
            aidat.delete()
        print(f"  ✅ {aidat_sayisi} aidat silindi.")
    else:
        print("  Bağlı aidat bulunamadı.")
    
    depozito_hareketleri = DepozitoHareket.objects.filter(gider=instance)
    depozito_sayisi = depozito_hareketleri.count()
    
    if depozito_sayisi > 0:
        print(f"  {depozito_sayisi} adet depozito hareketi siliniyor...")
        for hareket in depozito_hareketleri:
            print(f"    - {hareket.depozito.daire} - {hareket.tutar} TL - {hareket.aciklama}")
            hareket.delete()
        print(f"  ✅ {depozito_sayisi} depozito hareketi silindi.")
    
    print(f"=== Gider silme işlemi tamamlandı ===\n")


@receiver(post_delete, sender=Gider)
def gider_silindikten_sonra_mesaj(sender, instance, **kwargs):
    """Gider silindikten sonra bilgi mesajı"""
    print(f"Gider başarıyla silindi: {instance}")


# ========== AİDAT ÖDEME SİGNALI ==========
@receiver(post_save, sender=Aidat)
def aidat_odeme_sonrasi_depozito(sender, instance, created, **kwargs):
    """
    Aidat ödeme durumu değiştiğinde (ödendi veya iptal) banka ve depozito hareketini yönetir.
    """
    # Eğer yeni kayıt değilse (güncelleme ise)
    if not created:
        try:
            # Eski kaydı al (refresh_from_db ile güncel veriyi al)
            eski = Aidat.objects.get(pk=instance.pk)
            
            # Ödeme durumu değişti mi?
            if eski.odeme_yapildi_mi != instance.odeme_yapildi_mi:
                if instance.odeme_yapildi_mi:
                    # Ödeme yapıldıysa
                    print(f"🔔 Signal: Aidat ödendi - {instance.daire} {instance.ay}/{instance.yil}")
                    
                    # Eğer ödeme tarihi yoksa bugünü ata
                    if not instance.odeme_tarihi:
                        instance.odeme_tarihi = date.today()
                    
                    # NOT: Sonsuz döngüyü önlemek için odeme_yap çağırmıyoruz
                    # Doğrudan banka ve depozito hareketlerini oluşturuyoruz
                    
                    # 1. Banka hareketi oluştur
                    ana_hesap = Banka.objects.filter(ana_hesap_mi=True).first()
                    if ana_hesap:
                        try:
                            BankaHareket.objects.create(
                                banka=ana_hesap,
                                hareket_tipi='gelir',
                                tutar=instance.tutar,
                                tarih=instance.odeme_tarihi,
                                aciklama=f"Aidat ödemesi - {instance.daire} - {instance.ay}/{instance.yil}",
                                aidat=instance,
                                kisi=instance.kim_odedi
                            )
                            # Banka bakiyesini güncelle
                            ana_hesap.guncel_bakiye = float(ana_hesap.guncel_bakiye) + float(instance.tutar)
                            ana_hesap.save()
                            print(f"  ✅ Banka hareketi oluşturuldu")
                        except Exception as e:
                            print(f"  ❌ Banka hareketi oluşturulamadı: {e}")
                    else:
                        print("  ❌ Ana hesap bulunamadı!")
                    
                    # 2. Depozito hareketi oluştur (yuvarlama farkı varsa)
                    if instance.yuvarlama_farki != 0:
                        depozito = Depozito.objects.filter(daire=instance.daire, durum='alindi').first()
                        if depozito:
                            fark = float(instance.yuvarlama_farki)
                            try:
                                DepozitoHareket.objects.create(
                                    depozito=depozito,
                                    hareket_tipi='ekleme' if fark > 0 else 'cikarma',
                                    tutar=Decimal(str(abs(fark))),
                                    tarih=instance.odeme_tarihi or date.today(),
                                    aciklama=f"{instance.aciklama} (Yuvarlama farkı: {fark:+.2f} TL)",
                                    gider=instance.gider,
                                    aidat=instance
                                )
                                print(f"  ✅ Depozito hareketi oluşturuldu: {fark} TL")
                            except Exception as e:
                                print(f"  ❌ Depozito hareketi oluşturulamadı: {e}")
                        else:
                            print("  ❌ Depozito bulunamadı!")
                    else:
                        print("  Yuvarlama farkı 0, depozito işlemi atlandı")
                    
                else:
                    # Ödeme iptal edildiyse
                    print(f"🔔 Signal: Aidat ödemesi iptal edildi - {instance.daire} {instance.ay}/{instance.yil}")
                    
                    # Banka hareketlerini sil
                    silinen_banka = BankaHareket.objects.filter(aidat=instance).delete()
                    print(f"  Silinen banka hareketi sayısı: {silinen_banka[0]}")
                    
                    # Depozito hareketlerini sil
                    if instance.gider:
                        silinen_depo = DepozitoHareket.objects.filter(gider=instance.gider, depozito__daire=instance.daire).delete()
                        print(f"  Silinen depozito hareketi sayısı: {silinen_depo[0]}")
                    
        except Aidat.DoesNotExist:
            pass
        except Exception as e:
            print(f"⚠️ Signal hatası: {e}")