(function(){
var $=function(i){return document.getElementById(i)},token=null,me=null,mode='s',styles=[],resetToken=null;
try{token=localStorage.getItem('mlab_token')}catch(e){}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}
var LABELS={rap_fr:'Rap français',drill:'Drill',trap:'Trap',rnb:'R&B',afrobeat:'Afrobeat',pop:'Pop urbaine',naturel:'Voix naturelle'};
var STATUS={pending:'En attente',processing:'Traitement en cours…',done:'Terminé',error:'Erreur'};

function api(path,opt){opt=opt||{};opt.headers=opt.headers||{};if(token)opt.headers.Authorization='Bearer '+token;
 return fetch(path,opt).then(function(r){
  if(r.status===401&&token){logout();throw new Error('Session expirée')}
  if(!r.ok)return r.json().catch(function(){return{}}).then(function(j){var d=j.detail;if(Array.isArray(d))d='Données invalides';var e=new Error(d||'Erreur '+r.status);e.status=r.status;throw e});
  return r.status===204?null:r;})}
function json(path,opt){return api(path,opt).then(function(r){return r&&r.json()})}
function blobUrl(path){return api(path).then(function(r){return r.blob()}).then(function(b){return URL.createObjectURL(b)})}

// wave
var w=$('wave');for(var i=0;i<40;i++){var b=document.createElement('i');b.style.animationDelay=(i*.07)+'s';b.style.animationDuration=(.9+(i%5)*.15)+'s';w.appendChild(b)}

// auth modal
function openAuth(m){mode=m;$('ov').classList.add('on');var s=m=='s',l=m=='l',f=m=='f',r=m=='r';
 $('atabs').hidden=f||r;$('t1').className=s?'a':'';$('t2').className=l?'a':'';
 $('ft').hidden=!(f||r);$('ft').textContent=f?'Mot de passe oublié':'Nouveau mot de passe';
 $('ln').hidden=$('n').hidden=!s;$('le').hidden=$('e').hidden=r;$('lp').hidden=$('p').hidden=f;
 $('lp').textContent=r?'Nouveau mot de passe (8 caractères min.)':'Mot de passe (8 caractères min.)';
 $('ago').textContent=s?'Créer mon compte':l?'Me connecter':f?'Envoyer le lien':'Changer le mot de passe';
 $('anote').hidden=!s;$('lf').parentNode.hidden=!l;$('aer').textContent='';$('aer').className='er';
 $('p').autocomplete=l?'current-password':'new-password'}
document.querySelectorAll('[data-signup]').forEach(function(x){x.onclick=function(){openAuth('s')}});
$('nb').onclick=function(){openAuth('s')};$('nl').onclick=function(e){e.preventDefault();openAuth('l')};
$('t1').onclick=function(){openAuth('s')};$('t2').onclick=function(){openAuth('l')};$('cl').onclick=function(){$('ov').classList.remove('on')};
$('lf').onclick=function(e){e.preventDefault();openAuth('f')};
function post(path,body){return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
 .then(function(r){return r.json().catch(function(){return{}}).then(function(j){if(!r.ok){var d=j.detail;throw new Error(typeof d=='string'?d:'Vérifie tes informations (e-mail valide, mot de passe 8+ caractères).')}return j})})}
function aerr(m,ok){$('aer').textContent=m;$('aer').className='er'+(ok?' ok':'')}
$('ago').onclick=function(){
 var n=$('n').value.trim(),e=$('e').value.trim(),p=$('p').value,mailOk=/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
 var done=function(){$('ago').disabled=false};
 if(mode=='f'){if(!mailOk)return aerr('Adresse e-mail invalide.');$('ago').disabled=true;
  return post('/auth/forgot',{email:e}).then(function(){aerr('Si cet e-mail existe, un lien vient d’être envoyé. Vérifie aussi tes spams.',1)}).catch(function(x){aerr(x.message)}).then(done)}
 if(mode=='r'){if(p.length<8)return aerr('Mot de passe : 8 caractères minimum.');$('ago').disabled=true;
  return post('/auth/reset',{token:resetToken,password:p}).then(function(){aerr('Mot de passe changé. Tu peux te connecter.',1);$('p').value='';history.replaceState(null,'','/');setTimeout(function(){openAuth('l')},1500)}).catch(function(x){aerr(x.message)}).then(done)}
 if(mode=='s'&&n.length<2)return aerr('Entre ton nom d’artiste.');
 if(!mailOk)return aerr('Adresse e-mail invalide.');
 if(p.length<8)return aerr('Mot de passe : 8 caractères minimum.');
 $('ago').disabled=true;
 post(mode=='s'?'/auth/register':'/auth/login',mode=='s'?{email:e,name:n,password:p}:{email:e,password:p})
 .then(function(j){token=j.token;try{localStorage.setItem('mlab_token',token)}catch(x){}$('p').value='';$('ov').classList.remove('on');boot()})
 .catch(function(x){aerr(x.message)}).then(done)};
function logout(){token=null;me=null;try{localStorage.removeItem('mlab_token')}catch(e){}$('app').hidden=true;$('pub').hidden=false}
$('out').onclick=logout;

// boot
function boot(){
 if(!token){$('pub').hidden=false;$('app').hidden=true;return}
 json('/me').then(function(u){me=u;$('pub').hidden=true;$('app').hidden=false;$('uname').textContent=u.name;banner();
  return json('/styles')}).then(function(s){styles=s;var sel=$('style');sel.innerHTML='';s.forEach(function(x){var o=document.createElement('option');o.value=x.key;o.textContent=LABELS[x.key]||x.key;sel.appendChild(o)});applyStyle()}).catch(function(){});
}
function banner(){var el=$('banner');
 if(me.sub_status==='active'||me.sub_status==='trialing'){el.innerHTML='<div class="bn">Abonnement actif.</div>';return}
 var d=new Date(me.trial_ends_at),left=Math.ceil((d-Date.now())/864e5);
 el.innerHTML=me.has_access?'<div class="bn">Essai gratuit : '+left+' jour'+(left>1?'s':'')+' restant'+(left>1?'s':'')+'.</div>':'<div class="bn w2">Ton essai est terminé. Abonne-toi (onglet Abonnement) pour continuer.</div>'}

// tabs
document.querySelectorAll('[data-tab]').forEach(function(t){t.onclick=function(){
 document.querySelectorAll('[data-tab]').forEach(function(x){x.className=x===t?'a':''});
 ['studio','projets','abo'].forEach(function(n){$('tab-'+n).hidden=n!==t.dataset.tab});
 if(t.dataset.tab=='projets')loadProjects();if(t.dataset.tab=='abo')loadBilling()}});

// studio
function applyStyle(){var k=$('style').value,s=styles.filter(function(x){return x.key==k})[0];if(!s)return;$('rev').value=Math.round(s.reverb*100);$('del').value=Math.round(s.delay*100);out()}
function out(){$('o1').textContent=$('intensity').value+' %';$('o2').textContent=$('bal').value+' dB';$('o3').textContent=$('rev').value+' %';$('o4').textContent=$('del').value+' %'}
$('style').onchange=applyStyle;['intensity','bal','rev','del'].forEach(function(i){$(i).oninput=out});
var busy=false;
$('go').onclick=function(){
 if(busy)return;var v=$('fv').files[0],ins=$('fi').files[0];$('er').textContent='';
 if(!v||!ins)return $('er').textContent='Choisis une voix et un instrumental.';
 var fd=new FormData();fd.append('name',$('pname').value.trim()||'Mon son');fd.append('style',$('style').value);
 fd.append('options',JSON.stringify({intensity:$('intensity').value/100,voice_balance_db:+$('bal').value,reverb:$('rev').value/100,delay:$('del').value/100}));
 fd.append('voice',v);fd.append('instru',ins);
 busy=true;$('go').disabled=true;$('prog').hidden=false;$('bar').style.width='0';$('st').textContent='Envoi des fichiers…';$('result').innerHTML='';
 var x=new XMLHttpRequest();x.open('POST','/projects');x.setRequestHeader('Authorization','Bearer '+token);
 x.upload.onprogress=function(e){if(e.lengthComputable)$('bar').style.width=Math.round(e.loaded/e.total*100)+'%'};
 x.onload=function(){var j={};try{j=JSON.parse(x.responseText)}catch(e){}
  if(x.status>=200&&x.status<300){$('prog').hidden=true;poll(j.id)}
  else{var d=j.detail;if(x.status===402&&me){me.has_access=false;banner()}fail(typeof d=='string'?d:'Envoi refusé')}};
 x.onerror=function(){fail('Problème de connexion')};x.send(fd)};
function fail(m){busy=false;$('go').disabled=false;$('prog').hidden=true;$('st').textContent='';$('er').textContent=m}
function poll(id){$('st').textContent=STATUS.pending;
 var t=setInterval(function(){json('/projects/'+id).then(function(p){
  $('st').textContent=STATUS[p.status]||p.status;
  if(p.status=='done'){clearInterval(t);busy=false;$('go').disabled=false;$('st').textContent='Terminé ✓';showResult(p)}
  if(p.status=='error'){clearInterval(t);fail('Le traitement a échoué. Vérifie tes fichiers et réessaie. Aucun crédit ni résultat fictif.')}
 }).catch(function(){clearInterval(t);fail('Impossible de suivre le traitement')})},2000)}
function player(label,id,kind){var h=document.createElement('div');h.innerHTML='<label>'+label+'</label>';var a=document.createElement('audio');a.controls=true;h.appendChild(a);
 blobUrl('/projects/'+id+'/audio/'+kind).then(function(u){a.src=u}).catch(function(){h.innerHTML+='<p class="mu s">Indisponible</p>'});return h}
function dl(id,name){var bt=document.createElement('button');bt.className='btn g sm';bt.textContent='Télécharger';
 bt.onclick=function(){blobUrl('/projects/'+id+'/audio/mix').then(function(u){var a=document.createElement('a');a.href=u;a.download=name+'.mp3';a.click()})};return bt}
function showResult(p){var r=$('result');r.innerHTML='<div class="c"><h3>Résultat : '+esc(p.name)+'</h3></div>';var c=r.firstChild;
 c.appendChild(player('Mix final (traité)',p.id,'mix'));c.appendChild(player('Voix originale',p.id,'voice'));c.appendChild(player('Instrumental',p.id,'instru'));
 var row=document.createElement('div');row.className='row';row.appendChild(dl(p.id,p.name));c.appendChild(row);
 var m=document.createElement('p');m.className='mu s';m.textContent='Style : '+(LABELS[p.style]||p.style)+'. Ajuste les réglages ci-dessus et relance pour comparer. Le projet est enregistré dans Projets.';c.appendChild(m)}

// projets
function loadProjects(){var box=$('tab-projets');box.innerHTML='<p class="mu">Chargement…</p>';
 json('/projects').then(function(list){box.innerHTML='';if(!list.length){box.innerHTML='<div class="c"><p>Aucun projet pour l’instant.</p></div>';return}
  list.forEach(function(p){var c=document.createElement('div');c.className='c';
   c.innerHTML='<h3>'+esc(p.name)+'</h3><span class="pill '+p.status+'">'+(STATUS[p.status]||p.status)+'</span> <span class="pill">'+esc(LABELS[p.style]||p.style)+'</span> <span class="pill">'+new Date(p.created_at).toLocaleDateString('fr-FR')+'</span>';
   var row=document.createElement('div');row.className='row';
   if(p.status=='done'){var pl=document.createElement('button');pl.className='btn g sm';pl.textContent='Écouter';pl.onclick=function(){pl.replaceWith(player('Mix',p.id,'mix'))};row.appendChild(pl);row.appendChild(dl(p.id,p.name))}
   var rn=document.createElement('button');rn.className='btn g sm';rn.textContent='Renommer';rn.onclick=function(){var n=prompt('Nouveau nom',p.name);if(n)json('/projects/'+p.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})}).then(loadProjects)};row.appendChild(rn);
   var de=document.createElement('button');de.className='btn g sm';de.textContent='Supprimer';de.onclick=function(){if(confirm('Supprimer ce projet et ses fichiers ?'))api('/projects/'+p.id,{method:'DELETE'}).then(loadProjects)};row.appendChild(de);
   c.appendChild(row);box.appendChild(c)})}).catch(function(e){box.innerHTML='<div class="c"><p>'+esc(e.message)+'</p></div>'})}

// abonnement
function loadBilling(){var box=$('tab-abo');Promise.all([json('/me'),json('/config')]).then(function(r){var u=r[0],cfg=r[1];me=u;banner();
 var act=u.sub_status==='active'||u.sub_status==='trialing';
 box.innerHTML='<div class="c"><h3>MixLab AI : 30,99 €/mois</h3><p>'+(act?'Abonnement actif.':u.has_access?'Essai gratuit en cours jusqu’au '+new Date(u.trial_ends_at).toLocaleDateString('fr-FR')+'.':'Essai terminé.')+'</p><div id="ab" class="row"></div><p class="mu s" id="am"></p></div>';
 var ab=$('ab');function add(t,fn,cls){var b=document.createElement('button');b.className=cls||'btn';b.textContent=t;b.onclick=fn;ab.appendChild(b)}
 if(act){if(u.provider=='paypal')add('Annuler mon abonnement PayPal',cancelPP,'btn g');else add('Gérer / annuler mon abonnement',function(){go('/billing/portal')})}
 else{if(cfg.stripe)add('S’abonner par carte',function(){go('/billing/checkout')});
  if(cfg.paypal)add('S’abonner avec PayPal',function(){go('/billing/paypal/subscribe')});
  if(!cfg.stripe&&!cfg.paypal)$('am').textContent='Le paiement n’est pas encore activé sur ce site.'}}).catch(function(e){box.innerHTML='<div class="c"><p>'+esc(e.message)+'</p></div>'})}
function go(p){json(p,{method:'POST'}).then(function(j){location.href=j.url}).catch(function(e){$('am').textContent=e.message})}
function cancelPP(){if(!confirm('Annuler ton abonnement PayPal ? L’accès s’arrête.'))return;json('/billing/paypal/cancel',{method:'POST'}).then(loadBilling).catch(function(e){$('am').textContent=e.message})}
boot();
var qs=new URLSearchParams(location.search);
if(qs.get('reset')){resetToken=qs.get('reset');openAuth('r')}
else if(qs.get('paypal')=='ok'){history.replaceState(null,'','/');if(token)json('/billing/paypal/confirm',{method:'POST'}).then(function(){return json('/me')}).then(function(u){me=u;banner()}).catch(function(){})}
else if(qs.get('ok')||qs.get('paypal')){history.replaceState(null,'','/')}
})();
