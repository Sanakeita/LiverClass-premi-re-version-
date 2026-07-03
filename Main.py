#!/usr/bin/env python3
"""
LiverClass - Application web Flask pour Mister Liver Digital Lab.
Plateforme de vente et gestion de formations en ligne (gratuites & MVP).
Un seul fichier, templates intégrés, base SQLite.
Lancer avec : pip install flask flask-sqlalchemy && python app.py
"""

import os
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, render_template_string, request, redirect,
    url_for, flash, session, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# ---------- Configuration ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///liverclass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}

# Création du dossier uploads si inexistant
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ---------- Modèles de données ----------
class Formation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    prix = db.Column(db.Integer, nullable=False)  # en GNF
    version = db.Column(db.String(10), nullable=False)  # 'gratuit' ou 'mvp'
    date_session = db.Column(db.DateTime, nullable=False)
    plateforme = db.Column(db.String(20), nullable=False)  # zoom, teams, meet
    lien_direct = db.Column(db.String(500), nullable=False)
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    inscriptions = db.relationship('Inscription', backref='formation', lazy=True)

class Inscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    formation_id = db.Column(db.Integer, db.ForeignKey('formation.id'), nullable=False)
    capture_paiement = db.Column(db.String(200))  # nom du fichier uploadé
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, confirme, refuse
    date_inscription = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    date_validation = db.Column(db.DateTime, nullable=True)

# ---------- Décorateurs de sécurité ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            flash('Veuillez vous connecter en tant qu\'administrateur.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        expected = os.environ.get('API_KEY', 'secret-key')
        if not api_key or api_key != expected:
            return jsonify({'error': 'Clé API invalide ou manquante'}), 403
        return f(*args, **kwargs)
    return decorated

# ---------- Utilitaires ----------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def plateforme_icon(plateforme):
    icons = {'zoom': '🔵', 'teams': '🟣', 'meet': '🟢'}
    return icons.get(plateforme, '❓')

# ---------- Contexte pour les templates ----------
@app.context_processor
def inject_globals():
    return dict(plateforme_icon=plateforme_icon)

# ---------- Templates HTML embarqués ----------
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LiverClass - Mister Liver Digital Lab</title>
    <style>
        :root {
            --navy: #0a1f44;
            --gold: #d4af37;
            --white: #ffffff;
            --light-gray: #f8f9fa;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--light-gray); color: #333; }
        header { background: var(--navy); color: var(--white); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        header a { color: var(--white); text-decoration: none; margin: 0 0.5rem; }
        .logo { font-size: 1.8rem; font-weight: bold; color: var(--gold); }
        nav a { padding: 0.5rem 1rem; border-radius: 5px; transition: background 0.3s; }
        nav a:hover { background: rgba(212, 175, 55, 0.2); }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .flash { padding: 1rem; margin-bottom: 1rem; border-radius: 5px; }
        .flash.success { background: #d4edda; color: #155724; }
        .flash.danger { background: #f8d7da; color: #721c24; }
        .flash.warning { background: #fff3cd; color: #856404; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }
        .card { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 1.5rem; display: flex; flex-direction: column; justify-content: space-between; }
        .card h3 { color: var(--navy); margin-bottom: 0.5rem; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 15px; font-size: 0.8rem; font-weight: bold; margin: 0.5rem 0; }
        .badge-gratuit { background: #28a745; color: white; }
        .badge-mvp { background: var(--gold); color: var(--navy); }
        .btn { display: inline-block; padding: 0.5rem 1rem; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 0.9rem; }
        .btn-primary { background: var(--navy); color: white; }
        .btn-gold { background: var(--gold); color: var(--navy); font-weight: bold; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.8rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: var(--navy); color: white; }
        tr:hover { background: #f1f1f1; }
        form { max-width: 500px; margin: 2rem auto; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.3rem; font-weight: bold; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 5px; }
        .flex { display: flex; gap: 1rem; align-items: center; }
        .mt-2 { margin-top: 1rem; }
        @media (max-width: 768px) {
            header { flex-direction: column; gap: 1rem; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <header>
        <div class="logo">LiverClass</div>
        <nav>
            <a href="/">📚 Catalogue</a>
            <a href="/live">🔴 Live</a>
            {% if session.admin %}
                <a href="/admin/dashboard">⚙️ Admin</a>
                <a href="/admin/logout">Déconnexion</a>
            {% else %}
                <a href="/admin/login">🔐 Admin</a>
            {% endif %}
        </nav>
    </header>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# ---------- Routes publiques ----------
@app.route('/')
def catalogue():
    version_filter = request.args.get('version', 'toutes')
    query = Formation.query
    if version_filter == 'gratuit':
        query = query.filter_by(version='gratuit')
    elif version_filter == 'mvp':
        query = query.filter_by(version='mvp')
    formations = query.order_by(Formation.date_creation.desc()).all()

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>Catalogue des formations</h1>
    <div class="flex">
        <a href="?version=toutes" class="btn {% if version_filter=='toutes' %}btn-primary{% else %}btn-secondary{% endif %} btn-sm">Toutes</a>
        <a href="?version=gratuit" class="btn {% if version_filter=='gratuit' %}btn-primary{% else %}btn-secondary{% endif %} btn-sm">Gratuites</a>
        <a href="?version=mvp" class="btn {% if version_filter=='mvp' %}btn-primary{% else %}btn-secondary{% endif %} btn-sm">MVP</a>
    </div>
    <div class="grid">
        {% for f in formations %}
        <div class="card">
            <div>
                <h3>{{ f.titre }}</h3>
                <span class="badge {% if f.version=='gratuit' %}badge-gratuit{% else %}badge-mvp{% endif %}">
                    {{ f.version.upper() }}
                </span>
                <p>{{ f.description[:150] }}{% if f.description|length>150 %}...{% endif %}</p>
                <p><strong>Prix :</strong> {% if f.prix==0 %}Gratuit{% else %}{{ f.prix }} GNF{% endif %}</p>
                <p><strong>Session :</strong> {{ f.date_session.strftime('%d/%m/%Y %H:%M') }}</p>
            </div>
            <a href="/formation/{{ f.id }}" class="btn btn-primary mt-2">S'inscrire</a>
        </div>
        {% else %}
        <p>Aucune formation disponible pour le moment.</p>
        {% endfor %}
    </div>
    """)
    return render_template_string(template, version_filter=version_filter, formations=formations, plateforme_icon=plateforme_icon)

@app.route('/formation/<int:id>', methods=['GET', 'POST'])
def inscription(id):
    formation = Formation.query.get_or_404(id)
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        if not nom or not telephone:
            flash('Nom et téléphone sont obligatoires.', 'danger')
            return redirect(request.url)

        capture_filename = None
        if formation.version == 'mvp':
            file = request.files.get('capture_paiement')
            if not file or file.filename == '':
                flash('La capture de paiement est obligatoire pour les formations MVP.', 'danger')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                capture_filename = filename
            else:
                flash('Type de fichier non autorisé (jpg, jpeg, png, pdf).', 'danger')
                return redirect(request.url)

        statut = 'confirme' if formation.version == 'gratuit' else 'en_attente'
        inscription = Inscription(
            nom=nom,
            telephone=telephone,
            formation_id=formation.id,
            capture_paiement=capture_filename,
            statut=statut,
            date_validation=datetime.now(timezone.utc) if statut == 'confirme' else None
        )
        db.session.add(inscription)
        db.session.commit()
        flash('Inscription réussie !' + (' Votre accès est confirmé.' if statut == 'confirme' else ' Votre paiement est en attente de validation.'), 'success')
        return redirect(url_for('catalogue'))

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>Inscription à : {{ formation.titre }}</h1>
    <p>{{ formation.description }}</p>
    <p><strong>Version :</strong> {{ formation.version.upper() }} | <strong>Prix :</strong> {% if formation.prix==0 %}Gratuit{% else %}{{ formation.prix }} GNF{% endif %}</p>
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>Nom complet</label>
            <input type="text" name="nom" required>
        </div>
        <div class="form-group">
            <label>Téléphone</label>
            <input type="text" name="telephone" required>
        </div>
        {% if formation.version == 'mvp' %}
        <div class="form-group">
            <label>Capture d'écran du paiement (jpg/png/pdf)</label>
            <input type="file" name="capture_paiement" accept=".jpg,.jpeg,.png,.pdf" required>
        </div>
        {% endif %}
        <button type="submit" class="btn btn-primary">Valider l'inscription</button>
    </form>
    <a href="/" class="btn btn-secondary mt-2">Retour au catalogue</a>
    """)
    return render_template_string(template, formation=formation)

@app.route('/live')
def live():
    formations = Formation.query.filter_by(actif=True).order_by(Formation.date_session).all()
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>🟢 Sessions Live actives</h1>
    {% if formations %}
    <div class="grid">
        {% for f in formations %}
        <div class="card">
            <h3>{{ plateforme_icon(f.plateforme) }} {{ f.titre }}</h3>
            <p>{{ f.description[:100] }}{% if f.description|length>100 %}...{% endif %}</p>
            <p><strong>Plateforme :</strong> {{ f.plateforme|capitalize }}</p>
            <p><strong>Début :</strong> {{ f.date_session.strftime('%d/%m/%Y %H:%M') }}</p>
            <a href="{{ f.lien_direct }}" target="_blank" class="btn btn-gold mt-2">🔗 Rejoindre la session</a>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p>Aucune session live active pour le moment.</p>
    {% endif %}
    """)
    return render_template_string(template, formations=formations)

# ---------- Espace Admin ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        expected = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if password == expected:
            session['admin'] = True
            flash('Connexion réussie.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Mot de passe incorrect.', 'danger')
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>Connexion Admin</h1>
    <form method="POST">
        <div class="form-group">
            <label>Mot de passe</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-primary">Se connecter</button>
    </form>
    """)
    return render_template_string(template)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('catalogue'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    statut_filter = request.args.get('statut', 'tous')
    query = Inscription.query
    if statut_filter != 'tous':
        query = query.filter_by(statut=statut_filter)
    inscriptions = query.order_by(Inscription.date_inscription.desc()).all()
    formations = Formation.query.order_by(Formation.date_creation.desc()).all()

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>Tableau de bord Admin</h1>
    <div class="flex mt-2">
        <a href="?statut=tous" class="btn btn-sm {% if statut_filter=='tous' %}btn-primary{% else %}btn-secondary{% endif %}">Tous</a>
        <a href="?statut=en_attente" class="btn btn-sm {% if statut_filter=='en_attente' %}btn-warning{% else %}btn-secondary{% endif %}">En attente</a>
        <a href="?statut=confirme" class="btn btn-sm {% if statut_filter=='confirme' %}btn-success{% else %}btn-secondary{% endif %}">Confirmés</a>
        <a href="?statut=refuse" class="btn btn-sm {% if statut_filter=='refuse' %}btn-danger{% else %}btn-secondary{% endif %}">Refusés</a>
    </div>

    <h2 class="mt-2">📋 Inscriptions</h2>
    <table>
        <tr>
            <th>ID</th><th>Nom</th><th>Téléphone</th><th>Formation</th><th>Version</th><th>Statut</th><th>Date</th><th>Actions</th>
        </tr>
        {% for ins in inscriptions %}
        <tr>
            <td>{{ ins.id }}</td>
            <td>{{ ins.nom }}</td>
            <td>{{ ins.telephone }}</td>
            <td>{{ ins.formation.titre }}</td>
            <td>{{ ins.formation.version.upper() }}</td>
            <td>{{ ins.statut }}</td>
            <td>{{ ins.date_inscription.strftime('%d/%m/%Y %H:%M') }}</td>
            <td class="flex" style="gap:0.3rem;">
                {% if ins.statut == 'en_attente' %}
                <a href="/admin/valider/{{ ins.id }}/confirme" class="btn btn-success btn-sm">✅</a>
                <a href="/admin/valider/{{ ins.id }}/refuse" class="btn btn-danger btn-sm">❌</a>
                {% endif %}
                {% if ins.capture_paiement %}
                <a href="/uploads/{{ ins.capture_paiement }}" target="_blank" class="btn btn-secondary btn-sm">📎</a>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <h2 class="mt-2">📚 Formations</h2>
    <a href="/admin/formation/ajouter" class="btn btn-primary">+ Nouvelle formation</a>
    <table>
        <tr>
            <th>ID</th><th>Titre</th><th>Version</th><th>Prix (GNF)</th><th>Actif</th><th>Actions</th>
        </tr>
        {% for f in formations %}
        <tr>
            <td>{{ f.id }}</td>
            <td>{{ f.titre }}</td>
            <td>{{ f.version.upper() }}</td>
            <td>{{ f.prix }}</td>
            <td>{{ 'Oui' if f.actif else 'Non' }}</td>
            <td>
                <a href="/admin/formation/toggle/{{ f.id }}" class="btn btn-sm {% if f.actif %}btn-secondary{% else %}btn-success{% endif %}">
                    {{ 'Désactiver' if f.actif else 'Activer' }}
                </a>
            </td>
        </tr>
        {% endfor %}
    </table>
    """)
    return render_template_string(template, inscriptions=inscriptions, formations=formations, statut_filter=statut_filter)

@app.route('/admin/formation/ajouter', methods=['GET', 'POST'])
@admin_required
def admin_ajouter_formation():
    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form['description']
        prix = int(request.form['prix'])
        version = request.form['version']
        date_session = datetime.strptime(request.form['date_session'], '%Y-%m-%dT%H:%M')
        plateforme = request.form['plateforme']
        lien_direct = request.form['lien_direct']
        actif = True  # par défaut actif

        formation = Formation(
            titre=titre,
            description=description,
            prix=prix,
            version=version,
            date_session=date_session,
            plateforme=plateforme,
            lien_direct=lien_direct,
            actif=actif
        )
        db.session.add(formation)
        db.session.commit()
        flash('Formation ajoutée avec succès.', 'success')
        return redirect(url_for('admin_dashboard'))

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <h1>Ajouter une formation</h1>
    <form method="POST">
        <div class="form-group"><label>Titre</label><input type="text" name="titre" required></div>
        <div class="form-group"><label>Description</label><textarea name="description" rows="4" required></textarea></div>
        <div class="form-group"><label>Prix (GNF)</label><input type="number" name="prix" value="0" required></div>
        <div class="form-group"><label>Version</label><select name="version" required>
            <option value="gratuit">Gratuit</option><option value="mvp">MVP</option>
        </select></div>
        <div class="form-group"><label>Date de session</label><input type="datetime-local" name="date_session" required></div>
        <div class="form-group"><label>Plateforme</label><select name="plateforme" required>
            <option value="zoom">Zoom</option><option value="teams">Teams</option><option value="meet">Meet</option>
        </select></div>
        <div class="form-group"><label>Lien direct</label><input type="url" name="lien_direct" required></div>
        <button type="submit" class="btn btn-primary">Ajouter</button>
    </form>
    """)
    return render_template_string(template)

@app.route('/admin/valider/<int:id>/<statut>')
@admin_required
def admin_valider_inscription(id, statut):
    if statut not in ('confirme', 'refuse'):
        flash('Statut invalide.', 'danger')
        return redirect(url_for('admin_dashboard'))
    inscription = Inscription.query.get_or_404(id)
    inscription.statut = statut
    inscription.date_validation = datetime.now(timezone.utc) if statut == 'confirme' else None
    db.session.commit()
    flash(f'Inscription {statut} avec succès.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/formation/toggle/<int:id>')
@admin_required
def admin_toggle_formation(id):
    formation = Formation.query.get_or_404(id)
    formation.actif = not formation.actif
    db.session.commit()
    flash(f'Formation {"activée" if formation.actif else "désactivée"}.', 'success')
    return redirect(url_for('admin_dashboard'))

# ---------- API REST ----------
@app.route('/api/formations', methods=['GET'])
@api_key_required
def api_formations():
    version = request.args.get('version')
    query = Formation.query
    if version and version in ('gratuit', 'mvp'):
        query = query.filter_by(version=version)
    formations = query.all()
    return jsonify([{
        'id': f.id,
        'titre': f.titre,
        'description': f.description,
        'prix': f.prix,
        'version': f.version,
        'date_session': f.date_session.isoformat(),
        'plateforme': f.plateforme,
        'lien_direct': f.lien_direct,
        'actif': f.actif,
        'date_creation': f.date_creation.isoformat()
    } for f in formations])

@app.route('/api/inscriptions', methods=['GET'])
@api_key_required
def api_inscriptions():
    statut = request.args.get('statut')
    version = request.args.get('version')
    query = Inscription.query.join(Formation)
    if statut:
        query = query.filter(Inscription.statut == statut)
    if version:
        query = query.filter(Formation.version == version)
    inscriptions = query.all()
    return jsonify([{
        'id': i.id,
        'nom': i.nom,
        'telephone': i.telephone,
        'formation': i.formation.titre,
        'version': i.formation.version,
        'statut': i.statut,
        'capture_paiement': i.capture_paiement,
        'date_inscription': i.date_inscription.isoformat(),
        'date_validation': i.date_validation.isoformat() if i.date_validation else None
    } for i in inscriptions])

@app.route('/api/inscriptions/<int:id>/valider', methods=['POST'])
@api_key_required
def api_valider_inscription(id):
    data = request.get_json()
    if not data or 'statut' not in data or data['statut'] not in ('confirme', 'refuse'):
        return jsonify({'error': 'Statut invalide'}), 400
    inscription = Inscription.query.get_or_404(id)
    inscription.statut = data['statut']
    inscription.date_validation = datetime.now(timezone.utc) if data['statut'] == 'confirme' else None
    db.session.commit()
    return jsonify({'message': f'Inscription {data["statut"]} avec succès'})

# ---------- Démarrage ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crée les tables si elles n'existent pas
    app.run(debug=True, host='0.0.0.0', port=5000)