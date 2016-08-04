from app import app, models, db, lm, forms
from flask import render_template, request, redirect, g, flash, session, url_for
from flask_login import current_user, login_user, login_required, logout_user
import urllib2

from bs4 import BeautifulSoup


@app.route('/')
@login_required
def index():
    return render_template("addmusic.html")

LAST_SIM_API = "http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist=%s&track=%s&user=sudomakeinstall&api_key=dff0458affbfe429e7a4113afd6cc257&autocorrect=1"
LAST_TRACK_INFO = "http://ws.audioscrobbler.com/2.0/?method=track.getinfo&artist=%s&track=%s&user=sudomakeinstall&api_key=dff0458affbfe429e7a4113afd6cc257&autocorrect=1"


def add_or_create_artist( name, url, mbid ):
    artist = models.Artist.query.filter_by(url=url).first()
    if artist:
        pass
    else:
        artist = models.Artist()
        artist.mbid = mbid
        artist.name = name
        artist.url = url
        db.session.add(artist)
        db.session.commit()
    return artist


def add_or_create_track(soup):
    url = soup.find('url', recursive=False).text
    tr = models.Track.query.filter_by(url=url).first()
    if tr:
        return tr
    else:
        # app.logger.warning("adding new track")
        tr = models.Track()
        tr.url = url
        tr.name = soup.find('name', recursive=False).text

        try:
            tr.mbid = soup.find('mbid', recursive=False).text
        except:
            tr.mbid = ""
            app.logger.warning(tr.name + " doesn't have mbid")

        try:
            tr.duration = soup.find('duration', recursive=False).text
        except:
            tr.duration = ""
            app.logger.warning(tr.name + " doesn't have duration")

        tr.playcount = soup.find('playcount', recursive=False).text

        try:
            tr.image = soup.find(size="large").text
        except:
            tr.image = ""
            app.logger.warning(tr.name + " doesn't have image")

        artist_name = soup.artist.find('name', recursive=False).text

        try:
            artist_mbid = soup.artist.find('mbid', recursive=False).text
        except:
            artist_mbid = ""
            app.logger.warning("artitst" + artist_name + " doesn't have mbid")

        artist_url = soup.artist.find('url', recursive=False).text

        artist = add_or_create_artist(artist_name, artist_url, artist_mbid)
        tr.artist = artist
        db.session.add(tr)
        db.session.commit()
        return tr


@app.before_request
def before_request():
    g.user = current_user

@lm.user_loader
def load_user(id):
    return models.User.query.get(int(id))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        # already logged in
        return redirect('/')
    form = forms.LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        session['remember_me'] = False
        # successful login
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is None:
            email = form.email.data
            user = models.User(nickname=email.split('@')[0],email = email)
            db.session.add(user)
            db.session.commit()
        remember = False
        if 'remember_me' in session:
            remember = session['remember_me']
            session.pop('remember_me',None)
        login_user(user, remember = remember)
        return redirect('/')
    return render_template('login.html',
                           form=form)


@app.route('/status')
@login_required
def status():
    dic = {}
    user_likes = models.UserLike.query.filter_by(user_id = g.user.id)
    liked_tracks = set()
    disliked_tracks = set()
    for x in user_likes:
        if x.like == 1:
            liked_tracks.add(x.track_id)
        elif x.like == -1:
            disliked_tracks.add(x.track_id)
    #set_tracks = set([x.track_id for x in user_likes if x.like == 1])
    links = models.TrackLink.query.all()
    for link in links:
        if link.to_id in dic:
            dic[link.to_id][1] = dic[link.to_id][1] + link.match
        elif link.from_id in liked_tracks and link.to_id not in liked_tracks and link.to_id not in disliked_tracks:
            t = models.Track.query.get(link.to_id)
            dic[link.to_id] = [t, link.match]
    tracks = list(dic.items())
    tracks.sort(key=lambda x:x[1][1], reverse=True)
    for i,x in enumerate(tracks):
        t = x[1][0]
        sims = [models.Track.query.get(link.from_id).name for link in sorted(t.back_sims,key=lambda x: x.match, reverse = True)]
        tracks[i][1].append(sims)
    #for track in tracks:
    #    app.logger.warning(repr(track[1]))
    return render_template('status.html',tracks=tracks)


def user_like_song(track_id, like):
    user_like = models.UserLike.query.filter_by(track_id=track_id, user_id=g.user.id).first()
    if user_like:
        app.logger.warning('user %d track %d already relation' % (g.user.id, track_id))
        if user_like.like == like:
            return
        else:
            user_like.like = like
            #db.session().commit()
            return
    app.logger.warning('user %d track %d creating relation'%(g.user.id,track_id))
    track = models.Track.query.get(track_id)
    edge = models.UserLike()
    edge.track_id = track_id
    edge.user_id = g.user.id
    edge.like = like
    track.users.append(edge)
    g.user.tracks.append(edge)
    #db.session.commit()
    app.logger.warning('user %d track %d finished' % (g.user.id, track_id))


@app.route('/updateSong', methods=['GET', 'POST'])
@login_required
def updateSong():
    if request.form['action'] == 'like':
        return likeSong(request.form["artist"], request.form["track"])
    elif request.form['action'] == 'ignore':
        user_like_song(int(request.form["track_id"]), -1)
        db.session.commit()
        return redirect('/status')


def likeSong(_artist, _track):
    ### get track info
    request_url = LAST_TRACK_INFO%(_artist,_track)
    request_url = request_url.replace(" ","%20")
    app.logger.warning(request_url)
    html = urllib2.urlopen(request_url).read()
    app.logger.warning("downloaded url")
    soup = BeautifulSoup(html, "lxml")
    soup = soup.lfm.track

    url = soup.find('url', recursive=False).text

    tr = add_or_create_track(soup)
    user_like_song(tr.track_id, 1)
    #db.session.commit()

    ### get similars
    request_url = LAST_SIM_API%(_artist,_track)
    request_url = request_url.replace(" ","%20")
    app.logger.warning(request_url)
    html = urllib2.urlopen(request_url).read()
    app.logger.warning("downloaded url")
    #app.logger.warning(html)
    soup = BeautifulSoup(html, "lxml")
    #tracks = []
    for x in soup.find_all('track'):
        match = float( x.match.text )
        if match < 0.01:
            continue
        t = add_or_create_track(x)
        if models.TrackLink.query.filter_by(from_id=tr.track_id,to_id=t.track_id).first():
            continue

        edge = models.TrackLink()
        edge.from_id = tr.track_id
        edge.to_id = t.track_id
        edge.match = x.match.text
        tr.sims.append(edge)
        t.back_sims.append(edge)

        #db.session.commit()
        #tracks.append(t)
        #app.logger.warning(repr( (track_name, playcount, mbid, match, url, duration, image, artist_name, artist_mbid, artist_url) ))
    db.session.commit()
    return redirect('/status')