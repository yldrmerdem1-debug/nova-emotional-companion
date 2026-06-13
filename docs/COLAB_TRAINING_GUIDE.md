# Colab Training Guide

Bu proje için Colab'de yapılacak işin amacı ham sohbet verisini modele çevirmek.

## 1. Yerelden Colab'e Yüklenecek Dosyalar

Önce bu dosyaları üret:

```powershell
cd backend
py generate_synthetic_training_data.py
```

Sonra Colab'e şu dosyaları yükle:

- `backend/app/data/generated/response_training_synthetic.jsonl`
- `backend/app/data/generated/brain_eval_synthetic.jsonl`
- `backend/app/data/generated/person_learning_synthetic.jsonl`
- `backend/app/data/response_training_corpus.jsonl` varsa
- `backend/app/data/turkish_style_corpus.json`

## 2. Veri Türleri

`response_training_synthetic.jsonl`

- Kullanıcı mesajı
- Brain state
- İdeal cevap
- Kötü cevap örnekleri
- Cevap üretim katmanı için kullanılır

`brain_eval_synthetic.jsonl`

- Kullanıcı mesajı
- Beklenen route / emotion / need / tone / style
- 24 joblib beynin test edilmesi için kullanılır

`person_learning_synthetic.jsonl`

- Kullanıcı konuşurken hangi kişisel tercih çıkarılmalı?
- Ne hafızaya alınmalı?
- Privacy varsa ne alınmamalı?
- Kullanıcı profili ve uzun süreli hafıza katmanı için kullanılır

## 3. İlk Aşamada Yeniden Eğitilecek Modeller

Yeterli veri birikince öncelik:

1. `intent_router_v1.joblib`
2. `need_classifier_v3.joblib`
3. `tone_classifier_v3.joblib`
4. `style_adapter_v2.joblib`
5. `privacy_classifier_v3.joblib`

Robot action modelleri daha sonra:

- `robot_action_selector_v3.joblib`
- `robot_action_face_v3.joblib`
- `robot_action_voice_tone_v3.joblib`

## 4. Colab'den Geri Alınacak Dosyalar

Eğitimden sonra yeni `.joblib` dosyalarını indirip buraya koy:

```text
backend/app/ml/models/
```

Dosya isimlerini bozma. Backend bu isimlerle yükler.

## 5. Önemli Kural

Kişisel veri sentetik üretilemez. Kişisel veri robotla konuşarak ve feedback vererek birikir.

Sentetik veri:

- Genel Türkçe
- Argo/rahat konuşma
- Kod
- Bilim
- Duygusal destek
- Privacy
- Stil

Gerçek kullanıcı verisi:

- Kullanıcının sevdiği hitap
- Sevmediği üslup
- Öğrenme seviyesi
- Projeleri
- Privacy sınırları

## 6. Hedef Mimari

```text
Mesaj
  -> TurkishBrainRouter
  -> Memory / User Profile / Knowledge retrieval
  -> ResponseGenerationService
  -> Feedback collection
  -> JSONL corpus
  -> Colab retraining
  -> new .joblib brains
```
