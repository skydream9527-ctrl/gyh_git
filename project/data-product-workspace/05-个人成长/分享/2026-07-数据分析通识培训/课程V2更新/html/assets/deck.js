(function(){
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var i=0,fi=0;var prog=document.getElementById('prog');
  function frags(s){return [].slice.call(s.querySelectorAll('.fragment'));}
  function render(){
    slides.forEach(function(s,idx){
      s.classList.toggle('active',idx===i);
      if(!s.querySelector('.kicker')&&s.dataset.kicker){var k=document.createElement('div');k.className='kicker';k.innerHTML=s.dataset.kicker+' <span class="n">/ '+String(slides.length).padStart(2,'0')+'</span>';s.appendChild(k);}
      if(!s.querySelector('.pageno')){var p=document.createElement('div');p.className='pageno';p.textContent=String(idx+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0');s.appendChild(p);}
    });
    var f=frags(slides[i]);f.forEach(function(el,idx){el.classList.toggle('on',idx<fi);});
    prog.style.width=(i/(slides.length-1)*100)+'%';location.hash='s'+(i+1);
  }
  function next(){var f=frags(slides[i]);if(fi<f.length){fi++;render();return;}if(i<slides.length-1){i++;fi=0;render();}}
  function prev(){if(fi>0){fi--;render();return;}if(i>0){i--;fi=frags(slides[i]).length;render();}}
  function go(n){i=Math.max(0,Math.min(slides.length-1,n));fi=0;render();}
  document.addEventListener('keydown',function(e){
    if(['ArrowRight','ArrowDown',' ','PageDown'].indexOf(e.key)>-1){e.preventDefault();next();}
    else if(['ArrowLeft','ArrowUp','PageUp'].indexOf(e.key)>-1){e.preventDefault();prev();}
    else if(e.key==='Home'){go(0);}else if(e.key==='End'){go(slides.length-1);}
    else if(e.key==='p'||e.key==='P'){window.print();}
    else if(e.key==='f'||e.key==='F'){if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}
  });
  document.getElementById('next').onclick=next;document.getElementById('prev').onclick=prev;
  var m=location.hash.match(/s(\d+)/);if(m){i=Math.min(slides.length-1,Math.max(0,parseInt(m[1])-1));}
  render();
})();
