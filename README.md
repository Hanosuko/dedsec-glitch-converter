# DEDSEC Glitch Converter

DEDSEC Glitch Converter — локальный конвертер изображений и видео в 1-битный glitch/dither стиль. Проект умеет обрабатывать файлы через командную строку и через локальный интерфейс в браузере.

## Что умеет

- Конвертирует изображения: JPG, JPEG, PNG, BMP, DIB, TIFF, WEBP, JP2, J2K, PBM, PGM, PPM, PXM, PNM, SR, RAS, TGA, GIF, ICO, AVIF.
- Конвертирует видео: MP4, AVI, MOV, MKV, WEBM, FLV, M4V, MPG, MPEG, WMV, 3GP, TS, MTS, M2TS.
- Сохраняет фото в PNG, JPG, WEBP, TIFF, BMP, TGA, JP2 и PNM-форматах.
- Сохраняет видео в MP4, AVI, MOV, MKV и WEBM.
- Показывает шкалу прогресса во время рендера видео на странице `/video`.
- Поддерживает дизеринг Floyd-Steinberg, Bayer Ordered, Atkinson и жесткий threshold.
- Добавляет glitch-смещения, CRT scanlines, VHS noise, pixel dispersion и datamosh.
- Запускает локальный web-интерфейс на `http://127.0.0.1:8765` для фото и отдельную страницу `http://127.0.0.1:8765/video` для видео.
- Сохраняет результаты в папку `dedsec_outputs`.

## Быстрый запуск

```bash
cd "dedsec style"
/usr/bin/python3 -m venv .venv39
.venv39/bin/python -m pip install -r requirements.txt
.venv39/bin/python dedsec_converter.py --gui
```

После запуска открой в браузере:

```text
http://127.0.0.1:8765
```

На macOS можно также открыть файл `run_dedsec_converter.command` двойным кликом. Он сам создаст окружение, поставит зависимости и запустит локальный интерфейс.

## Использование через командную строку

```bash
.venv39/bin/python dedsec_converter.py \
  --input "/path/to/input.jpg" \
  --output "dedsec_outputs/result" \
  --output-format webp \
  --dither floyd \
  --glitch 0.5 \
  --scanlines \
  --vhs \
  --dispersion
```

Для видео:

```bash
.venv39/bin/python dedsec_converter.py \
  --input "/path/to/video.mp4" \
  --output "dedsec_outputs/result" \
  --output-format avi \
  --glitch 0.45 \
  --fps 24
```

## Основные параметры

| Параметр | Описание |
| --- | --- |
| `--gui` | Запускает локальный браузерный интерфейс |
| `--input` | Путь к исходному изображению или видео |
| `--output` | Путь для результата |
| `--output-format` | Формат результата: например `png`, `webp`, `mp4`, `avi` |
| `--dither` | `floyd`, `ordered`, `atkinson`, `none` |
| `--glitch` | Интенсивность эффекта от `0.0` до `1.0` |
| `--scanlines` | Включает CRT-линии |
| `--vhs` | Включает VHS-шум |
| `--dispersion` | Включает рассыпание светлых пикселей |
| `--datamosh` | Включает datamosh-артефакты |
| `--fps` | FPS для выходного видео |

## Где лежат результаты

Если не указать `--output`, файлы сохраняются рядом с исходником или в `dedsec_outputs`, когда используется web-интерфейс.

## Документация

- [Гайд по локальному запуску](docs/LOCALHOST.md)
- [Структура проекта](docs/PROJECT_STRUCTURE.md)
