"""Named presets and immutable configuration history, kept outside the profile."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import uuid
from .settings import ROOT, normalize, save_json


class Presets:
    def __init__(self, path=ROOT/'presets.json'):
        self.path=Path(path)
        self.data={'presets':[], 'history':[]}
        if self.path.exists():
            data=json.loads(self.path.read_text())
            if not isinstance(data,dict) or any(not isinstance(data.get(k),list) for k in self.data):
                raise ValueError('Arquivo de presets inválido; o original foi preservado.')
            for key in ['presets','history']:
                seen=set()
                for item in data[key]:
                    if not isinstance(item,dict) or not all(k in item for k in ['id','name','settings']):
                        raise ValueError('Um preset está incompleto. O arquivo original foi preservado.')
                    if not isinstance(item['id'],str) or item['id'] in seen:
                        raise ValueError('Identificador de preset inválido ou duplicado.')
                    self.name(item['name']);normalize(item['settings']);seen.add(item['id'])
            self.data=data

    def commit(self): save_json(self.path,self.data)

    @staticmethod
    def name(value):
        if not isinstance(value,str):raise ValueError('O nome do preset precisa ser um texto.')
        value=value.strip()
        if not value or len(value)>80: raise ValueError('Use um nome de 1 a 80 caracteres.')
        return value

    def add(self,name,settings):
        name=self.name(name)
        if any(p['name'].casefold()==name.casefold() for p in self.data['presets']):
            raise ValueError('Já existe um preset com esse nome.')
        item=dict(id=uuid.uuid4().hex,name=name,settings=normalize(settings))
        self.data['presets'].append(item); self.commit()
        return item['id']

    def rename(self,ident,name):
        name=self.name(name)
        if any(p['id']!=ident and p['name'].casefold()==name.casefold() for p in self.data['presets']):
            raise ValueError('Já existe um preset com esse nome.')
        next(p for p in self.data['presets'] if p['id']==ident)['name']=name
        self.commit()

    def delete(self,ident):
        self.data['presets']=[p for p in self.data['presets'] if p['id']!=ident]; self.commit()

    def get(self,ident,history=False,require_image=True):
        item=next(p for p in self.data['history' if history else 'presets'] if p['id']==ident)
        s=normalize(item['settings'])
        if require_image and not Path(s['image']).is_file():
            raise ValueError('A imagem deste preset não foi encontrada. Restaure o arquivo ou selecione outra imagem.')
        return deepcopy(s)

    def remember(self,settings):
        s=normalize(settings)
        if self.data['history'] and self.data['history'][-1]['settings']==s: return
        self.data['history'].append(dict(id=uuid.uuid4().hex,name=datetime.now().isoformat(timespec='seconds'),settings=s))
        self.commit()
