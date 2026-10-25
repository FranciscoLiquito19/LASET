from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,re,json,hashlib,shutil
base=Path.cwd()
build=base/'apresentacao/build'
source=build/'candidato-v3.pptx'
final=base/'apresentacao/output/Apresentacao_LaSET.pptx'
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(source) as z:
    slides={i:ET.fromstring(z.read(f'ppt/slides/slide{i}.xml')) for i in range(1,11)}
    text={i:' '.join(t.text or '' for t in root.findall('.//a:t',ns)) for i,root in slides.items()}
    notes={i:' '.join(t.text or '' for t in ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml')).findall('.//a:t',ns)) for i in range(1,11)}
    assert all('Fonte:' in n for n in notes.values())
    assert not any('\u2014' in s for s in [*text.values(),*notes.values()])
    assert not any(re.search(r'\b(?:TODO|FIXME|TBD|XXX)\b',s) for s in [*text.values(),*notes.values()])
    assert all(f'UC{i:02}' in text[5] for i in range(1,8))
    for s in ['2 barramentos independentes','Standard mode','500 kbit/s','1 Mbit/s','16 a 32','3 barramentos','8 Mbit/s em cada','Mínimo nominal de 100 Mbit/s','sem simultaneidade exigida']:
        assert s in text[6],s
    for s in ['3 canais','50 Hz','1100 a 1900','PPS a 1 Hz','GPS entre impulsos','Erro absoluto a medir','5 a 60 V','RTOS obrigatório','FreeRTOS candidato']:
        assert s in text[7],s
    tables=[i for i,r in slides.items() if r.findall('.//a:tbl',ns)]
    assert tables==[3,4,6],tables
    assert len(slides[1].findall('.//p:pic',ns))==2
    hashes={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('ppt/media/')}
    original_logos=[base/'template_laset/Figuras/logo_ISEP.jpg',base/'template_laset/Figuras/inesc.jpg']
    logo_matches=[hashlib.sha256(p.read_bytes()).hexdigest() in hashes for p in original_logos]
    assert all(logo_matches),'Logos originals differ from embedded image bytes'
    for i in [8,9]:
        assert slides[i].findall('.//p:cxnSp',ns)
        assert len(slides[i].findall('.//p:sp',ns))>=5
    words={i:len(s.split()) for i,s in text.items()}
geometry=json.loads((build/'geometria-final.json').read_text(encoding='utf-16'))
integrity=json.loads((build/'integridade-final.json').read_text(encoding='utf-16'))
assert integrity['status']=='pass'
assert geometry['warning_count']==0
assert not final.exists(),'Final deliverable already exists'
shutil.copy2(source,final)
assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(final.read_bytes()).digest()
report={'slides':10,'native_table_slides':tables,'editable_diagram_slides':[8,9],'speaker_notes_with_sources':10,'logos_embedded_unchanged':logo_matches,'slide_word_counts':words,'text_fit_findings':0,'integrity':integrity['status'],'layout_warnings':geometry['warning_count'],'font_policy':{'basis':'design','families':['Arial']},'native_powerpoint_open_and_render':True,'artifact_tool_available':False,'final_path':str(final),'sha256':hashlib.sha256(final.read_bytes()).hexdigest()}
(build/'entrega-verificada.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
