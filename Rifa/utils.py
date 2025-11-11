import uuid
import os
from re import sub
import logging
logger = logging.getLogger('ballena')

def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join('uploads', filename)


def slugify(s):
  s = s.lower().strip()
  s = sub(r'[^\w\s-]', '', s)
  s = sub(r'[\s_-]+', '-', s)
  s = sub(r'^-+|-+$', '', s)
  return s

def generate_slug(nombre_rifa, RifaModel):
  logger.debug('utils.py - generate_slug - starting a generate slug')
  base_slug = slugify(nombre_rifa)
  is_used_slug = True
  counter = 0
  new_slug = base_slug
  while(is_used_slug):
    new_slug = f"{base_slug}{'-'+str(counter) if counter > 0 else ''}"
    logger.debug(f"utils.py - generate_slug - new generated slug = {new_slug}")
    is_used_slug = RifaModel.objects.filter(NombreEnlace=new_slug, Eliminada=False).count() > 0
    if is_used_slug:
       counter+=1
  logger.debug(f"utils.py - generate_slug - returning slug = {new_slug}")
  return new_slug

