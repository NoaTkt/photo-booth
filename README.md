# PhotoBooth Windows tactile

Application Python Photobooth pour Windows avec interface tactile et impression.

## Contenu

- `main.py` : orchestration principale
- `camera_agent.py` : gestion de la caméra / capture
- `photo_agent.py` : sauvegarde et overlay photo
- `print_agent.py` : impression Windows
- `ui_agent.py` : interface tactile PySide6
- `requirements.txt` : dépendances
- `photos/` : dossier de sauvegarde des photos

## Prérequis

- Windows 10 ou supérieur
- Caméra compatible avec OpenCV
- Imprimante par défaut configurée

## Installation

1. Créez et activez un environnement Python :

```powershell
python -m venv .venv.\.venv\Scripts\Activate.ps1
```

2. Installez les dépendances :

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Utilisation

```powershell
python main.py
```

- Appuyez sur `Prendre photo` pour capturer une image.
- Appuyez sur `Imprimer` pour envoyer la dernière photo à l'imprimante par défaut.

## Notes

- Les photos sont sauvegardées dans le dossier `photos/`.
- L'impression utilise `pywin32` et la commande Windows `ShellExecute`.
- Si la caméra ne se lance pas, vérifiez l'index de la caméra (`camera_index=0`) dans `main.py`.


## Crée fichier application
- pyinstaller --onefile --windowed --icon=icon.ico main.py
- pyinstaller --onefile --windowed --icon=icon.ico main.py --collect-all PySide6
## Suppr ancien build :
- rmdir /s /q build
rmdir /s /q dist
del main.spec
