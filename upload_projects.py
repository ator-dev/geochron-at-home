import os, sys, shutil
from optparse import OptionParser
from django.db import transaction
import json

def ensuredir(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def copyimages(src, dst, grain):
    img_ext = { '.png' : 'P', '.jpeg': 'J', '.jpg': 'J' }
    ensuredir(dst)
    total_image = 0
    names = sorted(os.listdir(src))
    for n in names:
        srcname = os.path.join(src, n)
        is_image = False
        ext = os.path.splitext(n)[1]
        if os.path.isfile(srcname) and ext in img_ext:
            is_image = True
            with open(srcname, mode='rb') as f:
                im = Image(grain=grain, format=img_ext[ext], data=f.read())
                im.save()
            total_image+=1
        if is_image or n == 'rois.json':
            dstname = os.path.join(dst, n)
            shutil.copy2(srcname, dstname)


def creategrain(src, sample):
    p = os.path.join(src, 'rois.json')
    if not os.path.isfile(p):
        sys.exit('no such grain file {0}; exiting'.format(p))
    with open(p, mode='r') as j:
        rois = json.load(j)
    g = Grain(sample=sample, image_width=rois['image_width'], image_height=rois['image_height'])
    g.save()
    for r in rois['regions']:
        shift = r['shift']
        region = Region(grain=g, shift_x=shift[0], shift_y=shift[1])
        region.save()
        for v in r['vertices']:
            vertex = Vertex(region=region, x=v[0], y=v[1])
            vertex.save()
    return g


def copygrains(src, dst, sample):
    # create sample
    folders = next(os.walk(src))[1]
    total_grain = 0
    names = sorted(os.listdir(src))
    for name in names:
        srcname = os.path.join(src, name)
        if os.path.isdir(srcname):
            dstname = os.path.join(dst, name)
            grain = creategrain(srcname, sample)
            copyimages(srcname, dstname, grain)
            total_grain += 1
    sample.total_grains = total_grain
    sample.save()


def copysamples(src, dst, project):
    names = sorted(os.listdir(src))
    for name in names:
        srcname = os.path.join(src, name)
        if os.path.isdir(srcname):
            dstname = os.path.join(dst, name)
            sample = project.sample_set.create(sample_name=name,
                sample_property='T', total_grains=0, completed=False)
            copygrains(srcname, dstname, sample)


@transaction.atomic
def copyprojects(src, dst):
    folders = next(os.walk(src))[1]
    # create projects
    for name in folders:
        mystr = 'Project "%s" created by %s' % (name, uname)
        mystr = '*' + mystr.center(len(mystr)+6, ' ') + '*'
        print('*'*len(mystr))
        print(mystr)
        print('*'*len(mystr))
        p = Project(project_name=name, creator=user, project_description='project '+name, closed=False)
        p.save()
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        copysamples(srcname, dstname, p)


usage = "usage: %prog -s SETTINGS | --settings=SETTINGS"
parser = OptionParser(usage)
parser.add_option('-s', '--settings', dest='settings', metavar='SETTINGS',
                  help="The Django settings module to use")
parser.add_option('-i', '--input', dest='input', metavar='INPUT_DIRECTORY',
        help='The directory that contains the new files')
parser.add_option('-o', '--output', dest='output', metavar='OUTPUT_DIRECTORY',
        help='The directory to copy the new files to')
(options, args) = parser.parse_args()
if not options.settings:
    parser.error("You must specify a settings module. For examples, python standalone_django.py --settings=geochron.settings")

os.environ['DJANGO_SETTINGS_MODULE'] = options.settings

import django
django.setup()

from django.contrib.auth.models import User
from ftc.models import Project, Sample, Grain, Image, Region, Vertex

# get user id based on username
input_source_path = options.input or '/code/user_upload/'
grain_pool_path = options.output or '/code/static/grain_pool' #'irradiation/static/grain_pool'
uname = 'john'
u = User.objects.filter(username=uname)
if len(u) != 1:
    sys.exit('no user or too many users found')
user = u[0]

#----- walk through the project ------
input_source_path = os.path.normpath(input_source_path)
grain_pool_path = os.path.normpath(grain_pool_path)

src = os.path.join(input_source_path, uname)
dst = os.path.join(grain_pool_path, uname)

copyprojects(src, dst)
print('finished' + '-'*72)


