import subprocess
import sys
from pathlib import Path
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import threading
import schedule
import time
import os
import json



# Stelle sicher, dass spotdl installiert ist
def ensure_spotdl_installed():
    try:
        subprocess.run(["spotdl", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ spotdl ist bereits installiert.")
    except FileNotFoundError:
        print("⬇️ spotdl wird installiert...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "spotdl"])

def ensure_ffmpeg_installed():
    """Überprüft, ob FFmpeg installiert ist, und installiert es bei Bedarf."""
    try:
        # Überprüfe, ob FFmpeg installiert ist
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ FFmpeg ist bereits installiert.")
    except FileNotFoundError:
        print("⬇️ FFmpeg wird mit `spotdl --download-ffmpeg` installiert...")
        try:
            # Installiere FFmpeg mit spotdl
            subprocess.run(["spotdl", "--download-ffmpeg"], check=True)
            print("✅ FFmpeg wurde erfolgreich mit `spotdl` installiert.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Fehler: FFmpeg konnte nicht mit `spotdl` installiert werden: {e}")
            sys.exit(1)

def get_config_path():
    """Gibt den Pfad zur Konfigurationsdatei zurück."""
    if getattr(sys, 'frozen', False):  # Wenn als EXE ausgeführt
        base_path = sys._MEIPASS
    else:  # Wenn als Python-Skript ausgeführt
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "config.json")

def get_playlists_state_path():
    """Gibt den Pfad zur Datei zurück, in der der Zustand der Playlists gespeichert wird."""
    if getattr(sys, 'frozen', False):  # Wenn als EXE ausgeführt
        base_path = sys._MEIPASS
    else:  # Wenn als Python-Skript ausgeführt
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "playlists_state.json")

def load_playlists_state():
    """Lädt den gespeicherten Zustand der Playlists. Erstellt die Datei, falls sie nicht existiert."""
    state_path = get_playlists_state_path()
    try:
        with open(state_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("⚠️ Warnung: 'playlists_state.json' nicht gefunden. Eine neue Datei wird erstellt.")
        with open(state_path, "w") as file:
            json.dump({}, file, indent=4)
        return {}

def save_playlists_state(state):
    """Speichert den aktuellen Zustand der Playlists."""
    state_path = get_playlists_state_path()
    with open(state_path, "w") as file:
        json.dump(state, file, indent=4)

# Speichere die Zugangsdaten in einer Datei
def save_credentials(client_id, client_secret):
    """Speichert die Zugangsdaten in einer JSON-Datei."""
    config_path = get_config_path()
    with open(config_path, "w") as file:
        json.dump({"client_id": client_id, "client_secret": client_secret}, file)

# Lade die Zugangsdaten aus der Datei
def load_credentials():
    """Lädt die Zugangsdaten aus der JSON-Datei."""
    config_path = get_config_path()
    try:
        with open(config_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# GUI zur Eingabe von Zugangsdaten
def get_credentials_gui():
    credentials = {}

    def on_submit():
        client_id = client_id_entry.get().strip()
        client_secret = client_secret_entry.get().strip()

        if not client_id or not client_secret:
            messagebox.showerror("Fehler", "Client-ID und Client-Secret dürfen nicht leer sein!")
            return

        credentials["client_id"] = client_id
        credentials["client_secret"] = client_secret
        save_credentials(client_id, client_secret)
        window.destroy()

    window = tk.Tk()
    window.title("Spotify API Zugangsdaten")
    window.geometry("400x250")
    window.configure(bg="#122112")

    tk.Label(window, text="Gib deine Spotify-API-Zugangsdaten ein:", font=("Arial", 12), bg="#122112", fg="white").pack(pady=10)

    tk.Label(window, text="Client-ID:", bg="#122112", fg="white").pack(anchor="w", padx=10)
    client_id_entry = tk.Entry(window, width=40, bg="#254626", fg="white", insertbackground="white")
    client_id_entry.pack(padx=10, pady=5)

    tk.Label(window, text="Client-Secret:", bg="#122112", fg="white").pack(anchor="w", padx=10)
    client_secret_entry = tk.Entry(window, width=40, show="*", bg="#254626", fg="white", insertbackground="white")
    client_secret_entry.pack(padx=10, pady=5)

    submit_button = tk.Button(window, text="Bestätigen", command=on_submit, bg="#18b41d", fg="white", font=("Arial", 10, "bold"))
    submit_button.pack(pady=20)

    window.mainloop()
    return credentials

def get_all_playlists(sp):
    playlists = []
    results = sp.current_user_playlists()
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results["next"] else None


    if not playlists:
        messagebox.showinfo("Keine Playlists", "Es wurden keine Playlists gefunden.")
        return []
    


    return playlists

def choose_playlists_gui(playlists):
    selected_indexes = []

    def on_confirm():
        for idx, var in enumerate(variables):
            if var.get():
                selected_indexes.append(idx)
        window.destroy()

    window = tk.Tk()
    window.title("🎵 Wähle deine Playlists")

    canvas = tk.Canvas(window)
    frame = ttk.Frame(canvas)
    scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    variables = []
    for playlist in playlists:
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(frame, text=playlist.get('name', 'Unbekannte Playlist'), variable=var)
        cb.pack(anchor="w", padx=10, pady=2)
        variables.append(var)

    confirm_btn = ttk.Button(window, text="Herunterladen", command=on_confirm)
    confirm_btn.pack(pady=10)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame.bind("<Configure>", on_frame_configure)
    window.mainloop()

    return [playlists[i] for i in selected_indexes]

def download_playlist(playlist, output_folder):
    name = playlist.get('name', 'Unbekannt').strip().replace("/", "_")
    url = playlist.get('external_urls', {}).get('spotify', '')

    if not url:
        print(f"⚠️ Playlist '{name}' hat keine gültige URL. Übersprungen.")
        return

    folder = output_folder / name
    folder.mkdir(exist_ok=True)

    print(f"\n▶ Lade Playlist: {name}")
    try:
        subprocess.run(["spotdl", url, "--output", str(folder)], check=True)
        print(f"✅ Playlist '{name}' erfolgreich heruntergeladen.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler beim Herunterladen der Playlist '{name}': {e}")

def update_playlists(client_id, client_secret):
    """Aktualisiert die Playlists, indem nur neue Songs hinzugefügt und alte entfernt werden."""
    try:
        sp = Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="playlist-read-private playlist-read-collaborative",
            cache_path=".cache-" + client_id[:8]
        ))
    except Exception as e:
        messagebox.showerror("Fehler", f"Authentifizierung fehlgeschlagen: {e}")
        return

    all_playlists = get_all_playlists(sp)
    if not all_playlists:
        messagebox.showinfo("Keine Playlists", "Es wurden keine Playlists gefunden.")
        return

    # Lade den gespeicherten Zustand der Playlists
    playlists_state = load_playlists_state()

    desktop_path = Path.home() / "Desktop" / "Playlists"
    desktop_path.mkdir(parents=True, exist_ok=True)

    for playlist in all_playlists:
        playlist_name = playlist.get('name', 'Unbekannt').strip().replace("/", "_")
        playlist_id = playlist.get('id')
        playlist_folder = desktop_path / playlist_name
        playlist_folder.mkdir(exist_ok=True)

        # Hole die aktuellen Tracks der Playlist
        results = sp.playlist_tracks(playlist_id)
        current_tracks = {track['track']['id']: track['track']['name'] for track in results['items']}

        # Vergleiche mit dem gespeicherten Zustand
        previous_tracks = playlists_state.get(playlist_id, {})
        new_tracks = {track_id: name for track_id, name in current_tracks.items() if track_id not in previous_tracks}
        removed_tracks = {track_id: name for track_id, name in previous_tracks.items() if track_id not in current_tracks}

        # Lade neue Songs herunter
        for track_id, track_name in new_tracks.items():
            print(f"⬇️ Lade neuen Song herunter: {track_name}")
            # Hier kannst du den Download-Befehl für den Song einfügen
            # Beispiel: subprocess.run(["spotdl", track_name, "--output", str(playlist_folder)], check=True)

        # Entferne alte Songs
        for track_id, track_name in removed_tracks.items():
            print(f"❌ Entferne alten Song: {track_name}")
         # Suche nach der Datei im Ordner
        for file in playlist_folder.iterdir():
        # Überprüfe, ob der Dateiname den Tracknamen enthält
            if track_name in file.stem:  # Vergleiche den Namen ohne Erweiterung
                print(f"🗑️ Lösche Datei: {file}")
                file.unlink()  # Lösche die Datei
            break

        # Aktualisiere den gespeicherten Zustand
        playlists_state[playlist_id] = current_tracks

    # Speichere den aktualisierten Zustand der Playlists
    save_playlists_state(playlists_state)

    messagebox.showinfo("Fertig", "Playlists wurden aktualisiert.")

def job():
    print("Automatische Aktualisierung gestartet...")
    update_playlists(CLIENT_ID, CLIENT_SECRET)
    print("Automatische Aktualisierung abgeschlossen.")

def schedule_updates():
    """Plant die automatische stündliche Aktualisierung der Playlists."""
    # Plane die Aktualisierung jede Stunde
    schedule.every().hour.do(job)

    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    thread = threading.Thread(target=run_schedule, daemon=True)
    thread.start()

def create_combined_gui(client_id, client_secret):
    """Erstellt eine kombinierte GUI zur Auswahl der Playlists und zur Eingabe der Zugangsdaten."""
    selected_indexes = []
    playlists = []

    def load_playlists():
        """Lädt die Playlists des Benutzers."""
        try:
            sp = Spotify(auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="playlist-read-private playlist-read-collaborative",
                cache_path=".cache-" + client_id[:8]
            ))
            return get_all_playlists(sp)
        except Exception as e:
            messagebox.showerror("Fehler", f"Authentifizierung fehlgeschlagen: {e}")
            return []

    def on_download_click():
        """Startet das Herunterladen der ausgewählten Playlists."""
        if not selected_indexes:
            messagebox.showinfo("Hinweis", "Bitte wähle mindestens eine Playlist aus.")
            return

        desktop_path = Path.home() / "Desktop" / "Playlists"
        desktop_path.mkdir(parents=True, exist_ok=True)

        for index in selected_indexes:
            playlist = playlists[index]
            print(f"▶ Lade Playlist: {playlist.get('name', 'Unbekannt')}")
            download_playlist(playlist, desktop_path)

        messagebox.showinfo("Fertig", "Die ausgewählten Playlists wurden heruntergeladen.")

    def on_update_click():
        """Startet die Aktualisierung der ausgewählten Playlists."""
        if not selected_indexes:
            messagebox.showinfo("Hinweis", "Bitte wähle mindestens eine Playlist aus.")
            return

        update_playlists(client_id, client_secret)

    def on_playlist_select():
        """Aktualisiert die Liste der ausgewählten Playlists."""
        nonlocal selected_indexes
        selected_indexes = [idx for idx, var in enumerate(variables) if var.get()]

    def on_save_credentials():
        """Speichert die eingegebenen Zugangsdaten."""
        new_client_id = client_id_entry.get().strip()
        new_client_secret = client_secret_entry.get().strip()

        if not new_client_id or not new_client_secret:
            messagebox.showerror("Fehler", "Client-ID und Client-Secret dürfen nicht leer sein!")
            return

        save_credentials(new_client_id, new_client_secret)
        messagebox.showinfo("Erfolg", "Zugangsdaten wurden gespeichert.")
        nonlocal client_id, client_secret
        client_id = new_client_id
        client_secret = new_client_secret

    # Hauptfenster
    window = tk.Tk()
    window.title("Playlist-Manager")
    window.geometry("700x600")
    window.configure(bg="#f0f0f0")  # Hintergrundfarbe

    # Überschrift
    tk.Label(window, text="Playlist-Manager", font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#333").pack(pady=10)

    # Canvas für die Playlist-Auswahl
    canvas = tk.Canvas(window, bg="#ffffff", highlightthickness=0)
    frame = ttk.Frame(canvas)
    scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    variables = []
    playlists = load_playlists()

    for playlist in playlists:
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(frame, text=playlist.get('name', 'Unbekannte Playlist'), variable=var, command=on_playlist_select)
        cb.pack(anchor="w", padx=10, pady=2)
        variables.append(var)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame.bind("<Configure>", on_frame_configure)

    # Buttons
    button_frame = tk.Frame(window, bg="#f0f0f0")
    button_frame.pack(pady=20)

    download_button = tk.Button(
        button_frame,
        text="Playlists herunterladen",
        command=on_download_click,
        font=("Arial", 12, "bold"),
        bg="#4CAF50",
        fg="white",
        width=20,
        height=2
    )
    download_button.grid(row=0, column=0, padx=10)

    update_button = tk.Button(
        button_frame,
        text="Playlists aktualisieren",
        command=on_update_click,
        font=("Arial", 12, "bold"),
        bg="#2196F3",
        fg="white",
        width=20,
        height=2
    )
    update_button.grid(row=0, column=1, padx=10)

    # Eingabefelder für Zugangsdaten
    credentials_frame = tk.Frame(window, bg="#f0f0f0")
    credentials_frame.pack(side="bottom", pady=20, anchor="e", padx=20)

    tk.Label(credentials_frame, text="Client-ID:", bg="#f0f0f0", fg="#333").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    client_id_entry = tk.Entry(credentials_frame, width=30, bg="#ffffff", fg="#333")
    client_id_entry.insert(0, client_id)
    client_id_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(credentials_frame, text="Client-Secret:", bg="#f0f0f0", fg="#333").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    client_secret_entry = tk.Entry(credentials_frame, width=30, show="*", bg="#ffffff", fg="#333")
    client_secret_entry.insert(0, client_secret)
    client_secret_entry.grid(row=1, column=1, padx=5, pady=5)

    save_button = tk.Button(
        credentials_frame,
        text="Speichern",
        command=on_save_credentials,
        font=("Arial", 10, "bold"),
        bg="#4CAF50",
        fg="white"
    )
    save_button.grid(row=2, column=1, pady=10, sticky="e")

    window.mainloop()

def ensure_library_installed(library_name):
    """Überprüft, ob eine Bibliothek installiert ist, und installiert sie bei Bedarf."""
    try:
        __import__(library_name)
        print(f"✅ {library_name} ist bereits installiert.")
    except ImportError:
        print(f"⬇️ {library_name} wird installiert...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", library_name])

if __name__ == "__main__":
    # Überprüfe und installiere alle benötigten Bibliotheken
    required_libraries = ["spotipy", "schedule", "requests"]
    for lib in required_libraries:
        ensure_library_installed(lib)

    # Stelle sicher, dass spotdl installiert ist
    ensure_spotdl_installed()

    # Stelle sicher, dass FFmpeg installiert ist
    ensure_ffmpeg_installed()

    # Lade oder frage die Zugangsdaten ab
    credentials = load_credentials()
    if credentials:
        client_id = credentials["client_id"]
        client_secret = credentials["client_secret"]
    else:
        credentials = get_credentials_gui()
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        save_credentials(client_id, client_secret)

    # Setze die Zugangsdaten als globale Variablen
    global CLIENT_ID, CLIENT_SECRET
    CLIENT_ID = client_id
    CLIENT_SECRET = client_secret

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Fehler: Client-ID und Client-Secret sind erforderlich.")
        sys.exit(1)

    # Plane die automatische Aktualisierung
    schedule_updates()

    # Starte die kombinierte GUI
    create_combined_gui(CLIENT_ID, CLIENT_SECRET)