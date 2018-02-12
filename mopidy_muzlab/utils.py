# import requests
# import logging

# logger = logging.getLogger(__name__)

# def get_file_name(e):
#         return e[1].replace('\n', '')

# def download_tracks(playlist_url='http://muz-lab.ru/api/v1/stream/playlist_box',
# 					playlist_id):
# 	uri = '%s/%s' % (playlist_url, playlist_id)
# 	tempfile = '/tmp/tmp_playlist.m3u'

# 	logger.info('Download playlist !!!')
#     logger.info(uri)

#     try:
#         r = requests.get(uri, stream=True, timeout=(5, 60))
#     except requests.exceptions.ReadTimeout:
#         return logger.error('Error Read timeout occured')
#     except requests.exceptions.ConnectTimeout:
#         return logger.error('Error Connection timeout occured')

#     if r.status_code == 200:
#     	with open(tempfile, 'wb') as f:
#                 for chunk in r:
#                     f.write(chunk)

#     try:
#         assert(type(tempfile) == '_io.TextIOWrapper')
#     except AssertionError:
#         infile = open(tempfile,'r')
#     playlist_type = infile.readline()
#     if not playlist_type.startswith('#EXTM3U'):
#         return logger.error('Error playlist format')
#     playlist_number = infile.readline()
#     if not playlist_number.startswith('#PLAYLIST'):
#         return logger.error('Error playlist format')

#     lines = infile.readlines()
#     entry, notexists = [], []
#     for i,line in enumerate(lines):
#         if i%2 == 1:
#             continue
#         try:
#             e = [line, lines[i+1]]
#             if e[0].decode('utf-8').startswith('#EXTINF') and e[1].decode('utf-8').endswith('mp3\n'):
#                 if os.path.exists(get_file_name(e)) and os.stat(get_file_name(e)).st_size > 1024:
#                     entry.append(e)
#                 else:
#                     notexists.append(e)
#         except IndexError:
#             pass



