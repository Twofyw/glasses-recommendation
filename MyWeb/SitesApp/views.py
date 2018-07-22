import json
import os
import random
import string
import time
import uuid

import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import io
import cv2
import time

from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.template import loader
from django.urls import reverse

# 网站地址主页
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt


from MySites.settings import STATICFILES_DIRS, BASE_DIR, VISIT_PATH
from SitesApp.models import *
from utils.DBUtils import opeVoteRecordT, opeVoteTypeT, opeCandidateT, opeChatRecordT, opeReviewT, opeUserT

from utils.utils import getRandomColor, useMd5, getUserIP, voteCount, getFirstLetters

# fastai
from fastai.imports import *
from fastai.conv_learner import *
PATH = Path('data')
imspath = Path('img_align_celeba')
csv_fname = PATH/'list_train.csv'
sz=178
bs=64
arch=resnext50
tfms = tfms_from_model(arch, sz, aug_tfms=transforms_side_on, max_zoom=1.1)
trn_tfms, val_tfms = tfms
val_idxs = get_cv_idxs(12) # training set doesn't matter
data = ImageClassifierData.from_csv(str(PATH), str(imspath), str(csv_fname), bs=bs, tfms=tfms, val_idxs=val_idxs, 
                                    skip_header=True)
# model
learn = ConvLearner.pretrained(arch, data, precompute=False, ps=0.5, pretrained=True)
learn.load('1782')

# 查看用户是否已经登录
def checkLogin(request):
    # 从客户端cookie中拿到令牌
    utoken = request.COOKIES.get('utoken', None)
    if utoken:
        # 从服务端表中查找相同令牌的记录
        # print('utoken=',utoken)
        user = User.uManager.filter(uToken=utoken).first()

        # 如果确实有匹配的用户记录,则所有用户信息(状态)都可以访问
        if user:
            # print('user.token', user.uToken)
            return user
    return None


# 获取用户
def getUser(request):
    user = checkLogin(request)
    # 如果用户已经登录就返回该用户
    if user:
        # print('用户已经登录', user)
        return user
    ip = getUserIP(request)
    # print('获取用户ip', ip)
    # 如果用户已存在就返回该用户
    user = User.uManager.filter(uName=ip)
    # print('根据ip获取到的用户', user)
    if user.exists():
        return user.first()
    # 如果用户不存在就添加该用户
    opeUserT.add(uName=ip, uIP=ip)
    # 获取用户并返回
    return User.uManager.get(uName=ip)


# 主页地址路由处理函数
def index(request):
    # 反向解析，跳转到首页
    return redirect(reverse('SitesApp:grade'))


# 首页
# 使用Django原生缓存
# @cache_page(60,key_prefix='index',cache='default')

def home(request):
    voteType = opeVoteTypeT.query(vType__contains='编程').first()
    if voteType:
        # print(opeCandidateT.query(cVoteType_id=voteType.id).first().cIcon)
        # path = os.path.join(STATICFILES_DIRS[0], 'SitesApp','imgs','language')
        # list1 = os.listdir(path)
        dictData = {
            'imgs': opeCandidateT.query(cVoteType_id=voteType.id),
        }
    else:
        dictData = {
                'imgs':['glass1.png','glass2.png','glass3.png','glass4.png','glass5.png','glass6.png','glass7.png','php.jpg','ruby.jpg','易语言.jpg','汇编语言.jpg'],
        }

    return render(request, 'SitesApp/home.html', context=dictData)


# 投票
def vote(request, pageNum):
    # print('要第几页数据', pageNum)
    if not pageNum:
        pageNum = 1
    # 	获取用户IP
    ip = getUserIP(request)
    # 把本机地址传到页面，页面才能显示新增候选者按钮
    dictData = {'userName': getUser(request).uName}

    #  获取候选者
    candidates = Candidate.cManager.filter(cVoteType__vType__contains='编程').order_by('-cVotes')
    # 用户投票结果列表
    isVoteLists = []
    for candidate in candidates:
        # print(candidate.cName, '的票数为', candidate.cVotes)
        # 判断当前IP今天是否已经对该候选者投过票
        isVote = opeVoteRecordT.query(vCandidateId_id=candidate.id, isDelete=0, vTypeId_id=candidate.cVoteType_id,
                                      vComIP=ip,
                                      vDate=datetime.datetime.now().__format__('%Y-%m-%d'))

        if isVote.exists():
            isVoteLists.append(candidate.id)

    dictData['isVoteLists'] = isVoteLists
    # 获取留言信息
    chatRecords = ChatRecord.crManager.filter(crType=candidates.first().cVoteType_id)
    if chatRecords.exists():
        dictData['messages'] = chatRecords

    # 构建分页器对象,candidates=候选者列表,5=每页显示的个数
    paginator = Paginator(candidates, 5)
    # 获取第n页的页面对象
    page = paginator.page(pageNum)

    # Paginator和Page的常用API
    # page.previous_page_number()
    # page.next_page_number()
    # page.has_previous()
    # page.has_next()

    # 构造页面渲染的数据
    '''
    渲染需要的数据:
    - 当前页的候选者对象列表
    - 分页页码范围
    - 当前页的页码
    '''

    if request.method == 'GET':
        # 当前页的候选者对象列表
        dictData['page'] = page
        # 分页页码范围
        dictData['pagerange'] = paginator.page_range
        # 当前页的页码
        dictData['currentpage'] = page.number

    return render(request, 'SitesApp/vote.html', context=dictData)


# 增加投票数
def addVote(request):
    cid = request.GET.get('cid', None)
    if not cid:
        return JsonResponse({'status': 0, 'msg': 'no cid'})
    # 获取候选者信息
    candidate = Candidate.cManager.get(pk=cid)
    poills = candidate.cVotes
    ip = getUserIP(request)
    data = {'status': 0, 'msg': 'vote failed'}
    # 判断当前IP今天是否已经对该候选者投过票
    isVote = opeVoteRecordT.query(vCandidateId_id=cid, vTypeId__vType__contains='编程', vComIP=ip,
                                  vDate=datetime.datetime.now().__format__('%Y-%m-%d')).first()
    # isDelete初始值为0，表示记录没有被逻辑删除，用户再次点击投票就把记录删除，isDelete置为1
    if isVote:
        data['status'] = 2
        data['msg'] = 'already voted'
        # isDelete为True表示取消投票
        if isVote.isDelete:
            poills += 1
        else:
            poills -= 1
        # 修改投票记录
        if not opeVoteRecordT.modify(isVote.id, isDelete=not isVote.isDelete):
            # print('修改投票记录失败')
            return JsonResponse(data)
        # print('现在是取消(True)还是投票(False)', isVote.isDelete)
        # 修改候选者票数
        if not opeCandidateT.modify(candidate.id, cVotes=poills):
            # print('修改候选者记录失败')
            return JsonResponse(data)

    else:
        user = getUser(request)
        if not user:
            return JsonResponse(data)
        # 增加投票记录
        if not opeVoteRecordT.add(vUserId_id=user.id, vCandidateId_id=candidate.id, vComIP=ip,
                                  vTypeId_id=candidate.cVoteType_id, vPolls=1, vTimes=1):
            return JsonResponse(data)
        # 修改候选者票数
        if not opeCandidateT.modify(candidate.id, cVotes=candidate.cVotes + 1):
            return JsonResponse(data)
    data['status'] = 1
    data['msg'] = 'success'
    data['poills'] = poills
    return JsonResponse(data)


# 打分旧地址，重定向到新地址
def shareNav(request):
    return HttpResponseRedirect(reverse('SitesApp:grade', args=None, kwargs=None))

# 输入照片
def grade(request):
    return render(request, 'SitesApp/grade.html')

def predict_snap(fn):
    test_im = open_image('static/SitesApp/imgs/predict.jpg')
    test_im_norm = val_tfms(test_im)
    prediction = np.exp(learn.predict_array(test_im_norm[None]))[0][1]
    print(prediction)
    # prediction = 0.7
    return prediction

def grade_predict(request):
    cap = cv2.VideoCapture(0)
    time.sleep(2)
    ret, frame = cap.read()
    fn = 'static/SitesApp/imgs/predict.jpg'
    if ret:
        cv2.imwrite(fn, frame)
        # pass
    else:
        exit
    cap.release()

    prediction = predict_snap(fn) # 无框眼镜
    dictData = {
        'prediction': prediction,
        'complement_prediction': 1 - prediction,
    }

    return render(request, 'SitesApp/grade_predict.html', context=dictData)


# 增加分数
@csrf_exempt
def addGrade(request):

    whoId = request.POST.get('whoId', None)
    times = request.POST.get('times', None)
    grades = request.POST.get('grades', None)
    data = {'status': 0, 'msg': 'no whoId'}
    if not whoId:
        return JsonResponse(data)

    # 获取候选者信息
    candidate = Candidate.cManager.get(id=whoId)

    # 获取用户IP
    ip = getUserIP(request)
    user = getUser(request)

    # 判断用户是否已经打分,
    isVote = opeVoteRecordT.query(vTimes=times, vCandidateId_id=whoId, vComIP=ip,
                                  vDate=datetime.datetime.now().__format__('%Y-%m-%d')).first()
    if isVote:
        # print('已经投过票了')
        return JsonResponse({'status': 0, 'msg': 'already grade'})

    # 若用户还没有打分就添加打分记录
    if not opeVoteRecordT.add(vUserId_id=user.id, vCandidateId_id=candidate.id, vComIP=ip,
                              vTypeId_id=candidate.cVoteType_id, vPolls=grades, vTimes=times):
        # print('新增打分记录出错')
        return JsonResponse({'status': 0, 'msg': 'add voteRecord faild'})
    # 候选者打分人数加1
    if not opeCandidateT.modify(candidate.id, cVotes=candidate.cVotes + 1):
        # print('修改候选者记录出错')
        return JsonResponse({'status': 0, 'msg': 'modify candidateRecord faild'})
    # print('给谁打分', whoId, '第几轮', times, '多少分：', grades)
    # print('运行到这里啦')
    data = {'status': 1, 'msg': 'success'}
    # print(type(data), '***', data)
    return JsonResponse(data)


# 事项处理
@csrf_exempt
def review(request):
    # TODO
    dictData = {}
    # 处理GET请求
    if request.method == "GET":
        reviews = opeReviewT.query(rUserId_id=getUser(request).id)
        dictData['contents'] = reviews
        return render(request, 'SitesApp/review.html', context=dictData)

    changeRemark = request.POST.get('changeRemark', None)
    id = request.POST.get('id', None)
    remark = request.POST.get('remark', None)
    # 如果changeRemark为真，只修改rReamrk字段
    if changeRemark:
        if opeReviewT.modify(id=id,rRemark=remark):
            data = {'status': 1, 'ret': 'success'}
        else:
            data = {'status': 0, 'ret': 'faild'}
    else:
        topic = request.POST.get('topic', None)
        content = request.POST.get('content', None)
        impo = request.POST.get('impo', None)
        user = getUser(request)
        # 如果id存在，那么用户发起的请求就是修改记录的请求，否则是增加记录的请求
        if id:
            if opeReviewT.modify(id=id,rTopic=topic,rContent=content,rRemark=remark,rImpo=impo ):
                data = {'status': 1, 'ret': 'success'}
            else:
                data = {'status': 0, 'ret': 'faild'}
        else:
            if opeReviewT.add(rUserId=user,rTopic=topic,rContent=content,rRemark=remark,rImpo=impo):
                data = {'status': 1, 'ret': 'success'}
            else:
                data = {'status': 0, 'ret': 'faild'}

    return JsonResponse(data)


# 博客
def blog(request):
    # TODO
    return render(request, 'SitesApp/blog.html')


# 资料
def dataBank(request):
    # TODO
    return render(request, 'SitesApp/dataBank.html')


# 论坛
def forum(request):
    # TODO

    return render(request, 'SitesApp/forum.html')


# 登录
def login(request):
    if request.method == 'GET':
        return render(request, 'SitesApp/login.html')
    else:
        # 初始化返回信息
        respData = {'status': '0', 'ret': '登录失败，输入信息有误!!!'}

        # 预定义一个最终返回的Response对象(可以动态地为其配置内容,要想勒令客户端做事情必须要有一个Response对象)
        resp = HttpResponse()
        # 获取用户输入的用户名、密码、验证码
        uname = request.POST.get('uname', None)
        upwd = request.POST.get('upwd', None)
        vcode = request.POST.get('vcode', None)
        # 校验验证码
        # 从session中获取正确的验证码
        sessVcode = request.session.get('vcode', None)
        # 比较用户输入的验证码与正确的验证码是否匹配
        # 事先全部转换为小写形式,这样用户可以忽略大小写
        if vcode and sessVcode and vcode.lower() == sessVcode.lower():
            # 对密码做消息摘要
            upwd = useMd5(upwd)
            # 查询名称为uname的用户
            user = User.uManager.filter(uName=uname).first()
            if not user:
                respData = {'status': '0', 'ret': '用户不存在!!!'}
            # 检查密码、验证码是否匹配
            if user and upwd == user.uPwd:
                # # 勒令客户端(通过cookie)自己将状态保存起来,过期时间为60秒
                # resp.set_cookie('uname',uname,max_age=60*1)

                # # 让服务端通过session保存用户状态
                # 向客户端端要session其实是要存储在cookie中的sessionid
                # request.session的言下之意是"request.getSessionBySessionid"
                # request.session['uname'] = uname
                # request.session['upwd'] = upwd

                '''
                token相当于手动实现的session
                session将用户状态保存在django_session的表中
                token将用户状态保存在何处完全取决于程序媛自己,例如:User表
                但务必使保存用户状态的这张表中有用于作为[id/key/信物]的字段(该字段必须唯一),例如:utoken
                和session一样,必须在客户端的cookie中存一个相同的[id/key/信物],例如:utoken
                如何获取存储的用户状态:先从cookie中拿出utoken,进而查询User表中utoken为xxx的记录,就可以拿到uname了
                '''
                # 将用户状态保存在token中,让客户端持有一个token,将该token保存在某个表中
                # 生成令牌/信物
                token = str(uuid.uuid4())
                # 将该令牌/信物存储在客户端的cookie中,过期时间一天
                resp.set_cookie('utoken', token, expires=60 * 60 * 24)
                resp.set_cookie('uid', user.id, expires=60 * 60 * 24)
                # 将同样的信物存一份在服务端的表中
                user.uToken = token
                try:
                    user.save()
                    respData = {'status': '1', 'ret': 'login success!'}
                    # 获取用户访问的路径
                    visit_path = VISIT_PATH.get(getUserIP(request))
                    # print('visit_path', visit_path)
                    if visit_path:
                        VISIT_PATH.pop(getUserIP(request))
                    if not visit_path or visit_path == r'/app/login/':
                        respData['path'] = r'/app/mine/'
                    else:
                        respData['path'] = visit_path

                    # print('VISIT_PATH', VISIT_PATH)
                except BaseException as e:
                    # print(e)
                    pass
                    respData = {'status': '0', 'ret': '登录失败，输入信息有误!!!'}
        resp.content = json.dumps(respData)
        return resp


# 注册
def register(request):
    if request.method == 'GET':
        return render(request, 'SitesApp/register.html')
    else:
        # 获取用户输入的用户名、昵称、密码、验证码、上传的头像
        uname = request.POST.get('uname', None)
        unick = request.POST.get('unick', None)
        upwd = request.POST.get('upwd', None)
        vcode = request.POST.get('vcode', None)
        uip = getUserIP(request)
        # 拿到用户上传的文件数据,类型是框架类InMemoryUploadedFile
        uiconFile = request.FILES.get('uicon', None)
        # <class 'django.core.files.uploadedfile.InMemoryUploadedFile'>
        # print(uname, unick, upwd, vcode, uiconFile, type(uiconFile))

        # 手动存储上传的文件
        # 自定义文件位置
        # if uiconFile:
        # 	fp = os.path.join(MEDIA_ROOT, 'x-' + uiconFile.name)
        # 	# 写入文件
        # 	with open(fp, 'wb') as file:
        # 		# 逐"桶"读取上传的文件数据,并写入本地文件
        # 		for buffer in uiconFile.chunks():
        # 			file.write(buffer)

        # 校验验证码
        # 从session中获取正确的验证码
        sessVcode = request.session.get('vcode', None)
        # 比较用户输入的验证码与正确的验证码是否匹配
        # 事先全部转换为小写形式,这样用户可以忽略大小写
        if vcode and sessVcode and vcode.lower() == sessVcode.lower():
            user = User()
            user.uName = uname
            user.uNickName = unick
            user.uIP = uip
            # 对密码做消息摘要(目的是避免明文存储)
            user.uPwd = useMd5(upwd)

            # 将上传过来的文件直接赋值给用户的ImageField字段uicon
            # 框架会自动将图片存储在MEDIA_ROOT中
            if uiconFile:
                user.uIcon = uiconFile
            # 把数据写进数据库
            try:
                user.save()
                return JsonResponse({'status': 1, 'ret': 'register success!'})
            except BaseException as e:
                # print(e)
                pass

        return JsonResponse({'status': 0, 'ret': '输入信息有误!'})


# 我的
# @cache_page(60*3,key_prefix='indexs',cache='redis_special')
def mine(request):
    # # 从cookie中获取保存在客户端的用户状态
    # uname = request.COOKIES.get('uname',None)

    # #从服务端session获取用户状态
    # uname = request.session.get('uname',None)
    # # upwd = request.session.get('upwd',None)

    # 从token中获取用户状态

    uid = request.COOKIES.get('uid',None)
    if uid:
        content = cache.get('mine'+uid)
    else:
        content = None
    if not content:
        # time.sleep(5)
        user = getUser(request)
        if not user.uIcon:
            user.uIcon = "mine.png"
        dictData = {'user': user}
        template = loader.get_template('SitesApp/mine.html')
        content = template.render(context=dictData)
        cache.set('mine'+str(user.id), content)
        return HttpResponse(content)
    else:
        return HttpResponse(content)


    # user = getUser(request)
    # print('user login', user.uName)
    # if not user.uIcon:
    #     user.uIcon = "mine.png"
    # print('user uIcon', user.uIcon)
    # dictData = {'user': user}
    # return render(request, 'SitesApp/mine.html', context=dictData)


# 退出登录
@csrf_exempt
def logout(request):
    resp = HttpResponse()
    # 勒令客户端干掉自己保存的用户状态
    # resp.delete_cookie('uname')

    # #删除服务端session
    # # del request.session['uname']
    # request.session.flush()

    # 干掉token,勒令客户端删除自己的Cookie中的token
    resp.delete_cookie('utoken')
    uid = request.COOKIES.get('uid')
    uid = request.COOKIES.get('uid', None)
    if uid:
        content = cache.set('mine' + uid,None)

    resp.content = json.dumps({'status': '1'})

    return resp


# 测试
def test(request):
    print('富文本内容', request.GET.get('content'))
    rm = request.META
    dictData = {
        'dictData': rm
    }
    return render(request, 'SitesApp/test.html', context=dictData)


'''
生成并返回验证码
'''


def getvcode(request):
    # 随机生成验证码
    population = string.ascii_letters + string.digits
    letterlist = random.sample(population, 4)
    vcode = ''.join(letterlist)

    # 保存该用户的验证码
    request.session['vcode'] = vcode

    # 绘制验证码
    # 需要画布,长宽颜色
    image = Image.new('RGB', (176, 60), color=getRandomColor())
    # 创建画布的画笔
    draw = ImageDraw.Draw(image)
    # 绘制文字，字体所在位置
    path = os.path.join(BASE_DIR, 'static', 'fonts', 'ADOBEARABIC-BOLDITALIC.OTF')
    font = ImageFont.truetype(path, 50)

    for i in range(len(vcode)):
        draw.text((20 + 40 * i, 0), vcode[i], fill=getRandomColor(), font=font)

    # 添加噪声
    for i in range(500):
        position = (random.randint(0, 176), random.randint(0, 50))
        draw.point(position, fill=getRandomColor())

    # 返回验证码字节数据
    # 创建字节容器
    buffer = io.BytesIO()
    # 将画布内容丢入容器
    image.save(buffer, 'png')
    # 返回容器内的字节
    return HttpResponse(buffer.getvalue(), 'image/png')


# 留言
@csrf_exempt
def chat(request):
    cInfo = request.POST.get('cInfo')
    whoId = request.POST.get('whoId')
    # print('给谁留言', whoId)
    # 通过用户IP查找用户的名字
    ip = getUserIP(request)
    user = getUser(request)

    # 查找候选者
    candidate = Candidate.cManager.get(pk=whoId, isDelete=0)
    if opeChatRecordT.add(crUserId_id=user.id, crNickName=user.uNickName, crIP=ip, crInfo=cInfo, crTopic=candidate.id,
                          crType=candidate.cVoteType_id):
        return JsonResponse({'status': 1, 'msg': 'success'})
    return JsonResponse({'status': 0, 'msg': 'faild'})


# 增加候选者
@csrf_exempt
def addCandidate(request):
    if request.method == 'GET':
        voteTypes = VoteType.vManager.all()
        dictDaata = {
            'voteTypes': voteTypes
        }

        return render(request, 'SitesApp/addCondidate.html', context=dictDaata)
    newCandidate = Candidate()

    newCandidate.cName = request.POST.get('cName', None)
    cIcon = request.FILES.get('uicon', None)
    # print('上传的图像为', cIcon)
    if cIcon:
        newCandidate.cIcon = cIcon
    else:
        return JsonResponse({'status': 0, 'msg': '没上传头像'})
        # return HttpResponse('没上传头像')
    if not newCandidate:
        return JsonResponse({'status': 0, 'msg': '请输入姓名'})
        # return HttpResponse('请输入姓名')
    newCandidate.cPinyin = getFirstLetters(newCandidate.cName)
    voteType = VoteType.vManager.get(id=request.POST.get('vTypeId'))
    newCandidate.cVoteType = voteType
    try:
        newCandidate.save()
        if '编程' in voteType.vType:
            fp = os.path.join(STATICFILES_DIRS[0], 'SitesApp', 'imgs', 'language', cIcon.name)
            # 写入文件
            with open(fp, 'wb') as file:
                # 逐"桶"读取上传的文件数据,并写入本地文件
                for buffer in cIcon.chunks():
                    file.write(buffer)
            return redirect(reverse('SitesApp:vote'))
        elif '打分' in voteType.vType:
            return redirect(reverse('SitesApp:grade'))
        else:
            return redirect(reverse('SitesApp:home'))
    except BaseException as e:
        # print(e)
        pass
    return JsonResponse({'status': 0, 'msg': '添加失败'})
    # return HttpResponse('添加失败')
