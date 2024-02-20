from flask import Flask, render_template, url_for, request, redirect, session, Response # Potrebne biblioteke iz flask modula
from werkzeug.security import generate_password_hash, check_password_hash # Biblioteka za hesiranje lozinke
import mysql.connector # Sluzi za importovanje baze
import mariadb # Konekcija sa bazom
import ast # Abstract syntax tree  sluzi za  manipulisanje izrazima i strukturama koda
import html
import bcrypt

app = Flask(__name__) # Ako se ne deklarise ime, python uzima defoltno ime u kom se direktorijumu nalazi
app.secret_key = "tajni_kljuc_aplikacije" # app.secret_key sluzi za osiguravanje inegriteta podataka koji se cuvaju u sesijama

konekcija = mysql.connector.connect( # Kreiranje konekcije sa bazom
    passwd = "",
    user = "root",
    database = "prodaja_knjiga",
    port = 3306,
    auth_plugin = "mysql_native_password" # ako se koriste novije verzije
)

kursor = konekcija.cursor(dictionary=True) # Promenljivoj kursor sluzi za pokretanje konekcije sa bazom, i nad njom vrsimo upite

lozinke = {} # recnik za cuvanje hesiranih lozinka

def ulogovan(): # Globalna funkcija koja proverava da li je korisnik prijavljen tj. upisan u sesiji
    if "ulogovani_korisnik" in session:
        return True
    else :
        return False

def rola():
    if ulogovan():
        return ast.literal_eval(session["ulogovani_korisnik"]).pop("rola") 
      

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        forma = request.form
        upit = "SELECT * FROM korisnici WHERE email=%s"
        vrednost = (forma["email"],)
        kursor.execute(upit, vrednost) # funkcija kursor.execute koristi za izvršavanje SQL upita na bazi podataka
        korisnik = kursor.fetchone()
        if korisnik != None:
            # print(korisnik["lozinka"], forma["lozinka"], check_password_hash(korisnik["lozinka"], forma["lozinka"]))
            # print(korisnik["lozinka"].encode("utf-8"), forma["lozinka"].encode("utf-8"))
            if bcrypt.checkpw(forma["lozinka"].encode("utf-8"), korisnik["lozinka"].encode("utf-8")): # Proveravanje podudaranja lozinke
                session["ulogovani_korisnik"] = str(korisnik) # upisivanje korisnika u sesiji
                uloga = rola()  # Dobijanje uloge korisnika
                if uloga == "administrator":
                    return redirect(url_for("korisnici"))
                else:
                    return redirect(url_for("knjige"))
            else:
                return render_template("login.html")
        else:
            return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("ulogovani_korisnik", None)
    return redirect(url_for("login"))

@app.route("/korisnici", methods=["GET"])
def korisnici():
    if ulogovan():
        if rola() == "prodavac":
            return redirect(url_for("knjige"))
        if rola() == "kupac":
            return redirect(url_for("knjige"))
        if rola() == "administrator":
            upit = "SELECT * FROM korisnici"
            kursor.execute(upit)
            korisnici = kursor.fetchall()
            return render_template("korisnici.html", korisnici = korisnici)
        else:
            return redirect(url_for("login"))


@app.route("/knjige", methods=["GET"])
def knjige():
    if ulogovan():
        if rola() == "administrator":
            return redirect(url_for("korisnici"))
        else:    
            upit = "SELECT * FROM knjige"
            kursor.execute(upit)
            knjige = kursor.fetchall()
            return render_template("knjige.html", knjige=knjige, rola=rola())
    else:
        return redirect(url_for("login"))
    
@app.route("/kreiranje_naloga", methods=["GET","POST"])
def kreiranje_naloga():
    if ulogovan():
        if request.method == "GET":
            return render_template("kreiranje_naloga.html")
        elif request.method == "POST": # Preko post saljemo na serveru ime,prezime.. to sto smo definisali u formi kreiranje_naloga
            forma =  request.form # U promenljivu forma smestamo podatke iz forme definisane na stranici kreiranje naloga
            hesovana_lozinka = generate_password_hash(forma["lozinka"]) # iz polja lozinka definisane u kreiranje_naloga iscitaj i hesiraj i smesti u promenljivu hesovana_lozinka
            hesovana_lozinka = bcrypt.hashpw(forma["lozinka"].encode("utf-8"), bcrypt.gensalt())
            vrednosti = ( # vrednosti koje saljemo ka bazi za dodavanje novog korisnika saljemo kao vrednost tupla
                forma["ime"],
                forma["prezime"],
                forma["email"],
                hesovana_lozinka,
                forma["rola"]
            ) # Ovaj tupl saljemo na server prekoupita ispod

            upit = """ INSERT INTO 
                        korisnici(ime,prezime,email,lozinka,rola)
                        VALUES(%s,%s,%s,%s,%s)   """
            kursor.execute(upit, vrednosti) # uparujemo da bi radilo slanje ka serveru uparujemo upit i vrednosti jer se oni povezuju
            konekcija.commit() # za cuvanje trajno vrednosti koje smo uneli ka bazi

            return redirect(url_for("login"))
    else:
        return redirect(url_for("login"))    
    
@app.route("/dodavanje_knjige", methods=["GET","POST"])
def dodavanje_knjige():
    if ulogovan():
        if request.method == "GET":
            return render_template("dodavanje_knjige.html")
        elif request.method =="POST":
            forma = request.form
            vrednosti = (
                forma["naziv_knjige"],
                forma["autor"],
                forma["godina_izdanja"],
                forma["broj_strana"],
                forma["cena"]
            )
            upit = """ INSERT INTO
            knjige(naziv_knjige,autor,godina_izdanja,broj_strana,cena)
            values(%s,%s,%s,%s,%s)
            """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("knjige"))
    else:
        return redirect(url_for("login"))        



@app.route("/menjanje_korisnika/<id>", methods=["GET", "POST"]) #<id> se mora proslediti i u definiciji funkcije da bi nasli korisnika, stavljamo i id to je id korisnika jer da bi znali kog korisnika da menjamo
def menjanje_korisnika(id) ->'html':
    if ulogovan():
        if request.method == "GET":
            upit = "SELECT * FROM korisnici WHERE id=%s" # dobavaljamo tabelu korisnici iz baze ako pribavljamo korisnika sa GET mormamo proslediti id da bi u formi za menjanje podaci popune vrednostima koje zelimo da promenimo, vrednosti se kreiraju putem tupla
            vrednost = (id, ) # %s iznad ce se zameniti sa id, da bi definisali tupl sa jednom vrednoscu mora da stavimo zarez u suprotnom nece se kreirati tupl
            kursor.execute(upit, vrednost) # funkciji executu prosledjujemo upit i vrednost iznad
            korisnik = kursor.fetchone() #zovemo funkciju fetchone jer ce vratiti samo jedan podatak
            return render_template("menjanje_korisnika.html", korisnik = korisnik) # renderujemo templejt menjanje_korisnika, saljemo korisnika  koja je bila povratna vrednost upita da bi mogla popuniti podatke sa objektom korisnik
        if request.method == "POST": # sve ovo sa %s se zamenjuje koriscenjem tupla ispod vrednosti.. ime,prezime,email..
            upit = """ UPDATE korisnici SET
            ime = %s,
            prezime = %s, 
            email = %s, 
            lozinka = %s, 
            rola = %s
            WHERE id=%s 
            """     
            forma = request.form #dobavljamo podatke iz forme definisane u html stranici
            vrednosti = (
                forma["ime"], # ime,prezime,email.. se uzima iz forme iz korisnik_izmena.html , a id se uzima iz parametra funkcije
                forma["prezime"],
                forma["email"],
                forma["lozinka"],
                forma["rola"],
                id
                )
            kursor.execute(upit, vrednosti) #opet zovemo funkciju, ispod je komitujemo i na kraju se redirektujemo na korisnic
            konekcija.commit()
            return redirect(url_for('korisnici')) # render_korisnici je metoda , da bi nas vratila na stranicu korisnici ne mozemo navesti stranicu
    else:
        return redirect(url_for("login"))
    
@app.route('/izbrisi_korisnika/<id>', methods=["POST"]) #metoda je samo post jer zelimo samo da izbrisemo, moramo mu proslediti id da bi znao kojeg korinika da izbrise
def izbrisi_korisnika(id):
    if ulogovan():
        upit = """
                    DELETE FROM korisnici WHERE id=%s 
               """
        vrednost = (id,) # %s se odnosi na ovaj tupl ovde
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("korisnici")) # na kraju se redirektujemo na stranici korisnici  
    else:
        return redirect(url_for("login"))
    
@app.route("/menjanje_knjige/<id>", methods=["GET", "POST"]) #<id> se mora proslediti i u definiciji funkcije da bi nasli korisnika, stavljamo i id to je id korisnika jer da bi znali kog korisnika da menjamo
def menjanje_knjige(id) ->'html':
    if ulogovan():
        if request.method == "GET":
            upit = "SELECT * FROM knjige WHERE id=%s" 
            vrednost = (id, ) 
            kursor.execute(upit, vrednost) 
            knjiga = kursor.fetchone() #zovemo funkciju fetchone jer ce vratiti samo jedan podatak
            return render_template("menjanje_knjige.html", knjige = knjiga) 
        if request.method == "POST": 
            upit = """ UPDATE knjige SET
            naziv_knjige = %s,
            autor = %s, 
            godina_izdanja = %s, 
            broj_strana = %s, 
            cena = %s
            WHERE id=%s 
            """     
            forma = request.form #dobavljamo podatke iz forme definisane u html stranici
            vrednosti = (
                forma["naziv_knjige"], # ime,prezime,email.. se uzima iz forme iz korisnik_izmena.html , a id se uzima iz parametra funkcije
                forma["autor"],
                forma["godina_izdanja"],
                forma["broj_strana"],
                forma["cena"],
                id
                )
            kursor.execute(upit, vrednosti) 
            konekcija.commit()
            return redirect(url_for('knjige'))
    else:
        return redirect(url_for("login"))     
    
@app.route("/dodavanje_knjige_u_narudzbine/<id>", methods=["POST"])
def dodavanje_knjige_u_narudzbine(id):
    if ulogovan():
        upit_knjiga = "SELECT * FROM knjige WHERE id=%s"
        vrednost_knjiga = (id,)
        kursor.execute(upit_knjiga, vrednost_knjiga)
        knjiga = kursor.fetchone()

        if knjiga is not None:
            upit_narudzbina = """
                INSERT INTO narudzbine (naziv_knjige, autor, godina_izdanja, broj_strana, cena)
                VALUES (%s, %s, %s, %s, %s)
            """
            vrednosti_narudzbina = (
                knjiga["naziv_knjige"],
                knjiga["autor"],
                knjiga["godina_izdanja"],
                knjiga["broj_strana"],
                knjiga["cena"]
            )
            kursor.execute(upit_narudzbina, vrednosti_narudzbina)
            konekcija.commit()

        return redirect(url_for("narudzbine"))
    else:
        return redirect(url_for("login"))
      
@app.route("/brisanje_knjige_iz_narudzbine/<id>", methods=["POST"])
def brisanje_knjige_iz_narudzbine(id):
    if ulogovan():
        upit = "DELETE FROM narudzbine WHERE id=%s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("narudzbine"))
    else:
        return redirect(url_for("login"))

@app.route('/narudzbine', methods=["GET"])
def narudzbine():
    if ulogovan():
        if rola() == "administrator":
            return redirect(url_for("korisnici"))
        if rola() == "prodavac":
            return redirect(url_for("knjige"))
        if rola() == "kupac":
            upit = "SELECT * FROM narudzbine"
            kursor.execute(upit)
            narudzbine = kursor.fetchall()
            return render_template("narudzbine.html", narudzbine = narudzbine)
    else:
        return redirect(url_for("login"))

@app.route('/izbrisi_knjigu/<id>', methods=["POST"])
def izbrisi_knjigu(id):
    if ulogovan():
        upit = """
                    DELETE FROM knjige WHERE id=%s 
               """
        vrednost = (id,) 
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("knjige")) 
    else:
        return redirect(url_for("login"))    


app.run(debug=True)
    