# Структура проекта

```text
.
├── dedsec_converter.py
├── run_dedsec_converter.command
├── requirements.txt
├── README.md
└── docs
    ├── LOCALHOST.md
    └── PROJECT_STRUCTURE.md
```

## `dedsec_converter.py`

Главный файл приложения. В нем находятся:

- движок обработки изображений и видео;
- CLI-режим;
- локальный web-интерфейс для фото;
- отдельная localhost-страница `/video` для видео;
- обработка загрузок и выдача готовых файлов.

## `run_dedsec_converter.command`

Удобный запускатель для macOS. Его можно открыть двойным кликом.

## `requirements.txt`

Список Python-зависимостей:

- `opencv-python`;
- `numpy`;
- `pillow`.

## `dedsec_outputs`

Папка для результатов и временных загрузок. Она не публикуется в репозиторий.
