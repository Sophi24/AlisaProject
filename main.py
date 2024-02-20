import base64
import os
import re
import requests
import smtplib

from email.headerregistry import Address
from email.message import EmailMessage


def handler(event, context):
    user_request = 'empty'
    user_cond = '0'
    session_end = False
    text = ''

    user_mass = []

    # Проверка наличия состояния сессии и взятие значения из глобальной переменной даты
    if 'state' in event and \
            'session' in event['state'] and \
            'value' in event['state']['session']:
        user_mass = event['state']['session']['value']

    # Проверка наличия состояния сессии
    if 'state' in event and \
            'session' in event['state'] and \
            'condition' in event['state']['session']:
        user_cond = event['state']['session']['condition']

    # Проверка наличия сообщения от пользователя
    # original_utterance => command
    if 'request' in event and \
            'command' in event['request'] and \
            len(event['request']['command']) > 0:

        req = event['request']['command'].lower().strip()

        # help request
        if 'помощь' in req or 'что ты умеешь' in req:
            user_request = 'help'

        # Гороскоп
        elif req == 'основа':
            if user_cond == '2':
                user_request = 'OSN'
            else:
                user_request = 'error'

        # первая группа характеристик
        elif req in ['1', '2', '3', 'один', 'два', 'три']:
            if user_cond == '1':
                user_request = req
            else:
                user_request = 'error'

        elif req == 'дополнение':
            if user_cond == '1':
                user_request = 'DOP'
            else:
                user_request = 'error'

        # вторая группа характеристик
        elif req in ['4', '5', '6', 'четыре', 'пять', 'шесть']:
            if user_cond == '2':
                user_request = req
            else:
                user_request = 'error'

        # Письмо
        elif req == 'письмо':
            if user_cond in ['1', '2']:
                user_request = 'mail'
            else:
                user_request = 'error'

        elif req in ['почта яндекс аккаунта', 'авторизация']:
            if user_cond == '3':
                user_request = 'mail_yandex_avtor'
            else:
                user_request = 'error'

        elif req == 'готово':
            if user_cond == '31':
                user_request = 'mail_yandex_avtor'
            else:
                user_request = 'error'

        elif req in ['указать почту вручную', 'вручную', 'указать вручную']:
            if user_cond == '3':
                user_request = 'mail_user_input'
            else:
                user_request = 'error'

        elif user_cond == '32':
            user_request = 'mail_user_input_parse'
            req = event['request']['original_utterance'].lower().strip()

        # other => try date parse
        else:
            user_request = 'parse'
            user_mass_parse = req.split(' ')

    match user_request:

        case 'empty':
            text = 'Добро пожаловать в навык "Гороскоп Пифагора"!\n' + \
                   'На основе даты Рождения я смогу составить психоматрицу человека.\n' + \
                   'Чтобы начать составлять гороскоп назови дату Рождения. Например 6 августа 1990 года.'

        case 'help':
            text = help_get()
            user_cond = '0'

        case 'error':
            text = 'Некорректный ввод. Попробуй ещё раз.'

        case 'parse':
            text = 'Некорректный ввод. Попробуй ещё раз.'
            if len(user_mass_parse) >= 3:
                user_mass_parse[1] = month_text_to_int(user_mass_parse[1])
                if user_mass_parse[1] != 'error' and \
                        user_mass_parse[0].isdigit() == True and \
                        user_mass_parse[2].isdigit() == True and \
                        int(user_mass_parse[0]) > 0 and int(user_mass_parse[0]) <= 31 and \
                        int(user_mass_parse[2]) > 0 and int(user_mass_parse[0]) < 3000:
                    if user_mass_parse[1] == '02' and int(user_mass_parse[0]) > 29:
                        text = 'Некорректный ввод. Попробуй ещё раз.'
                    else:
                        user_cond = '1'

                        if len(user_mass_parse[0]) == 1:
                            user_mass_parse[0] = f'0{user_mass_parse[0]}'

                        user_mass = list()
                        user_mass.append(int(str(user_mass_parse[0])[:1]))
                        user_mass.append(int(str(user_mass_parse[0])[1:]))
                        user_mass.append(int(str(user_mass_parse[1])[:1]))
                        user_mass.append(int(str(user_mass_parse[1])[1:]))
                        user_mass.append(int(str(user_mass_parse[2])[:1]))
                        user_mass.append(int(str(user_mass_parse[2])[1:2]))
                        user_mass.append(int(str(user_mass_parse[2])[2:3]))
                        user_mass.append(int(str(user_mass_parse[2])[3:]))

                        text = 'Выбери раздел, назвав его номер: 1 - личность, 2 - интеллект, 3 - жизнь. \n Можешь перейти к дополнительному разделу, сказав дополнение.\n Если хочешь отправить гороскоп на почту, скажи письмо.'

        case 'OSN' | '1' | '2' | '3' | 'один' | 'два' | 'три':
            if user_request == 'OSN':
                text = 'Выбери раздел, назови его номер: 1 - личность, 2 - интеллект, 3 - жизнь. \n Можешь перейти к дополнительному разделу, сказав дополнение.\n Если хочешь отправить гороскоп на почту, скажи 0.'
            elif user_request in ['1', 'один']:
                text = LK(user_mass)
            elif user_request in ['2', 'два']:
                text = IS(user_mass)
            else:
                text = GO(user_mass)
            user_cond = '1'

        case 'DOP' | '4' | '5' | '6' | 'четыре' | 'пять' | 'шесть':
            if user_request == 'DOP':
                text = 'Выбери раздел, назвав его номер: 4 - внутренний мир, 5 - внешние факторы, 6 - индивидуальность \n Можешь перейти к основному разделу, сказав основа.\n Если хочешь отправить гороскоп на почту, скажи письмо.'
            elif user_request in ['4', 'четыре']:
                text = D1(user_mass)
            elif user_request in ['5', 'пять']:
                text = D2(user_mass)
            else:
                text = D3(user_mass)
            user_cond = '2'

        case 'mail':
            user_cond = '3'
            text = 'Выберите способ отправки письма на почту. Если хочешь отправить, авторизовавшись в Яндекс аккаунте, скажи "авторизация". Если хочешь указать почту вручную, скажи "вручную".'

        case 'mail_yandex_avtor':
            user_access_token = ''
            user_cond = '31'

            postmaster_token = os.environ.get('POST_TOKEN')

            # Пройдена ли авторизация (наличие токена)
            if 'session' in event and \
                    'user' in event['session'] and \
                    'access_token' in event['session']['user']:
                user_access_token = event['session']['user']['access_token']
                user_mail = get_sender_email_data(user_access_token)
                if not send_email(postmaster_token,
                                  'Гороскоп от Алисы', 'alisa.goroskop@yandex.ru',
                                  user_mail[1], 'Гороскоп для Вас от навыка Алисы',
                                  make_letter(user_mass)
                                  ):
                    text = 'Извините, не получилось отправить письмо. \n Если хотите попробовать отправить письмо ещё раз, скажите письмо.\n Если хотите начать заново, то введите дату рождения'
                    user_cond = '3'
                else:
                    text = f'Гороскоп отправлен на почту {user_mail[1]}.\nДля продолжения работы введите следующую дату рождения.'
                    user_cond = '0'

            # Авторизация если нет токена
            if user_access_token == '':
                text = 'Для отправки гороскопа на почту необходимо авторизоваться. \n После авторизации скажите Готово'

        case 'mail_user_input':
            user_cond = '32'
            text = 'Введите адрес почты'

        case 'mail_user_input_parse':
            user_cond = '3'
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
            if not re.fullmatch(regex, req):
                text = 'Извините, адрес неправильный! \n Выберите способ отправки письма на почту. Если хочешь отправить, авторизовавшись в Яндекс аккаунте, скажи "авторизация". Если хочешь указать почту вручную, скажи "вручную".'

            else:
                postmaster_token = os.environ.get('POST_TOKEN')
                if not send_email(postmaster_token,
                                  'Гороскоп от Алисы', 'alisa.goroskop@yandex.ru',
                                  req, 'Гороскоп для Вас от навыка Алисы',
                                  make_letter(user_mass)
                                  ):
                    text = 'Извините, не получилось отправить письмо. \n Выберите способ отправки письма на почту. Если хочешь отправить, авторизовавшись в Яндекс аккаунте, скажи "авторизация". Если хочешь указать почту вручную, скажи "вручную". \n Если хотите начать заново, то введите дату рождения'
                else:
                    text = f'Гороскоп отправлен на почту {req}.\nДля продолжения работы введите следующую дату рождения.'
                    user_cond = '0'

    resp = {
        'version': event['version'],
        'session': event['session'],
        'response': {
            'text': text,
            'end_session': session_end,
            'buttons': buttons_get(user_cond)
        },
        'session_state': {'value': user_mass, 'condition': user_cond}
    }

    # Запрос авторизации через Яндекс
    if user_cond == '31':
        resp['start_account_linking'] = {}

    return resp


def buttons_get(state_code):
    buttons = []
    match state_code:
        case '0':
            buttons.append({'title': 'Помощь', 'hide': True})
        case '1':
            buttons.append({'title': '1', 'hide': True})
            buttons.append({'title': '2', 'hide': True})
            buttons.append({'title': '3', 'hide': True})
            buttons.append({'title': 'Дополнение', 'hide': True})
            buttons.append({'title': 'Письмо', 'hide': True})
        case '2':
            buttons.append({'title': '4', 'hide': True})
            buttons.append({'title': '5', 'hide': True})
            buttons.append({'title': '6', 'hide': True})
            buttons.append({'title': 'Основа', 'hide': True})
            buttons.append({'title': 'Письмо', 'hide': True})
        case '3':
            buttons.append({'title': 'Авторизация', 'hide': True})
            buttons.append({'title': 'Вручную', 'hide': True})
        case '31':
            buttons.append({'title': 'Готово', 'hide': True})

    return buttons


def month_text_to_int(txt):
    txt = txt.lower()
    resp = "error"

    match txt:
        case "января":
            resp = "01"
        case "январь":
            resp = "01"
        case "февраля":
            resp = "02"
        case "февраль":
            resp = "02"
        case "марта":
            resp = "03"
        case "март":
            resp = "03"
        case "апреля":
            resp = "04"
        case "апрель":
            resp = "04"
        case "мая":
            resp = "05"
        case "май":
            resp = "05"
        case "июня":
            resp = "06"
        case "июнь":
            resp = "06"
        case "июля":
            resp = "07"
        case "июль":
            resp = "07"
        case "августа":
            resp = "08"
        case "август":
            resp = "08"
        case "сентября":
            resp = "09"
        case "сентябрь":
            resp = "09"
        case "октября":
            resp = "10"
        case "октябрь":
            resp = "10"
        case "ноября":
            resp = "11"
        case "ноябрь":
            resp = "11"
        case "декабря":
            resp = "12"
        case "декабрь":
            resp = "12"
    return resp


def LK(mass_in):
    matrix = baza(mass_in)

    # вводим ответы
    # Характер
    if matrix[0][0] == 0:
        text1 = 'Характер - слабо выражен. '
    elif matrix[0][0] == 1:
        text1 = 'Характер - мягкий, сниженная воля и ответственность. '
    elif matrix[0][0] == 2:
        text1 = ' Характер - деликатный, вежливый. Приятный в общении человек, который любит похвалу и знаки внимания. '
    elif matrix[0][0] == 3:
        text1 = 'Характер - умеренный, умеете быстро подстраиваться под обстоятельства.'
    elif matrix[0][0] == 4:
        text1 = 'Характер - характер прирожденного лидера, который способен руководить и брать на себя инициативу. '
    elif matrix[0][0] == 5:
        text1 = 'Характер - характер диктатора, который настолько стремится к своим целям, что не замечает никаких препятствий. '
    elif matrix[0][0] == 6:
        text1 = 'Характер - перегруженный характер, завышенные амбиции не реализуются из-за низкой целеустремленности. '
    else:
        text1 = ' Характер - человек все контролирует, но сам избегает ответственности. '

    # Энергия
    if matrix[1][0] == 0:
        text2 = 'Энергия - дефицит энергии, постоянное ощущение усталости, нехватка времени. '
    elif matrix[1][0] == 1:
        text2 = 'Энергия - постоянная суета, спешка, лень, прокрастинация, напрасная трата сил. '
    elif matrix[1][0] == 2:
        text2 = 'Энергия - активность, энергичность, общительная личность, которая все успевает и имеет широкий круг интересов. '
    else:
        text2 = 'Энергия - безграничный запас энергии, что позволяет быстро решать несколько задач сразу и оказывать влияние на людей. '

    # Здоровье
    if matrix[0][1] == 0:
        text4 = 'Здоровье - здоровье далеко от идеального, могут быть хронические заболевания, сниженный иммунитет, плохое зрение. '
    elif matrix[0][1] == 1:
        text4 = 'Здоровье - здоровый, устойчивый к болезням организм, и привлекательность. '
    elif matrix[0][1] == 2:
        text4 = 'Здоровье - скорее всего профессиональный спортсмен, выносливы и способны быстро восстанавливаться. '
    else:
        text4 = 'Здоровье - большая физическая сила, которая может переходить в агрессию. '

    text = f'{text1} \n{text2}\n{text4} '

    return text


def IS(mass_in):
    matrix = baza(mass_in)

    # вводим ответы
    # Интерес
    if matrix[2][0] == 0:
        text3 = 'Интерес - талант в творчестве. '
    elif matrix[2][0] == 1:
        text3 = 'Интерес - сложно выбрать одно направление, поэтому постоянно мечетесь между разными сферами. '
    elif matrix[2][0] == 2:
        text3 = 'Интерес - ярко выраженное стремление к получению знаний, особенно в области математики, техники, аналитики. '
    else:
        text3 = 'Интерес - есть способности для больших научных открытий, а также талант генерировать оригинальные идеи. '

    # Логика
    if matrix[1][1] == 0:
        text5 = 'Логика - мечтатель, который любит строить воздушные замки, но не умеет планировать. '
    elif matrix[1][1] == 1:
        text5 = 'Логика - способность мыслить логически и редко допускаете ошибки в своих расчетах. '
    elif matrix[1][1] == 2:
        text5 = 'Логика - острый ум и тонкое чутьё, способности стратега и аналитика. '
    else:
        text5 = 'Логика - перегруженная логика, при которой человека могут одолевать навязчивые мысли, перфекционизм '

    # Ум
    if matrix[2][2] == 0:
        text9 = 'Ум - слабая память, сложности в изложении своих мыслей. '
    elif matrix[2][2] == 1:
        text9 = 'Ум - способность запомнить лишь те сведения, которые требуются ему ежедневно. '
    elif matrix[2][2] == 2:
        text9 = 'Ум - способность помнить все детали. '
    else:
        text9 = 'Ум - мощный интеллектуальный потенциал, который в негативе реализуется как злопамятность. '

    text = f'{text3}\n{text5} \n{text9}'

    return text


def GO(mass_in):
    matrix = baza(mass_in)

    # вводим ответы
    # Труд
    if matrix[2][1] == 0:
        text6 = 'Труд - человек не любит заниматься монотонной ручной работой, а предпочитает зарабатывать своим умом. '
    elif matrix[2][1] == 1:
        text6 = 'Труд - есть способности шить, готовить, мастерить, но результат во многом зависит от запаса энергии. '
    elif matrix[2][1] == 2:
        text6 = 'Труд - мастер с золотыми руками, его профессия обычно связана с ремеслом. '
    else:
        text6 = 'Труд - склонности к оккультизму, умение управлять, манипулировать людьми. '

    # Удача
    if matrix[0][2] == 0:
        text7 = 'Удача - человек ничего не получает просто так, но это не означает глобальное невезение. '
    elif matrix[0][2] == 1:
        text7 = 'Удача - в жизни этого человека нередко случаются удачные совпадения. '
    elif matrix[0][2] == 2:
        text7 = 'Удача - постоянное присутствие удачи и защиту высших сил. '
    else:
        text7 = 'Удача - практически незамедлительно реализуются любые мысли, то есть и мечты, и страхи. '

    # Долг
    if matrix[1][2] == 0:
        text8 = 'Долг - человек склонен больше принимать, чем отдавать, ставить на первый план свои интересы, вести себя эгоистично. '
    elif matrix[1][2] == 1:
        text8 = 'Долг - способность ответственно выполнять работу, но в личной жизни старается избегать обязательств. '
    elif matrix[1][2] == 2:
        text8 = 'Долг - человек заботлив, добр, терпим, щедр, честен. '
    else:
        text8 = 'Долг - сильный контроль, гиперопека, религиозность. '

    text = f'{text6} \n{text7} \n{text8}'

    return text


def D1(mass_in):
    matrix = baza(mass_in)

    sum_num1 = matrix[0][0] + matrix[1][0] + matrix[2][0]
    sum_num2 = matrix[0][0] + matrix[1][1] + matrix[2][2]
    sum_num3 = matrix[2][0] + matrix[1][1] + matrix[0][2]

    text1 = ''
    text2 = ''
    text3 = ''

    # вводим ответы
    # Самооценка
    if sum_num1 < 4:
        text1 = 'Самооценка занижена.'
    elif sum_num1 < 6:
        text1 = 'Самооценка нормальная, здоровая.'
    elif sum_num1 > 5:
        text1 = 'Самооценка завышена.'

    # Духовность
    if sum_num2 < 2:
        text2 = 'Духовность - не придерживаетесь религии.'
    elif sum_num2 < 4:
        text2 = 'Духовность - относитесь нейтрально к религии.'
    elif sum_num2 > 3:
        text2 = 'Духовность - придерживаетесь религии.'

    # Темперамент
    if sum_num3 < 4:
        text3 = 'Темперамент - слабо выражен темперамент.'
    elif sum_num3 < 6:
        text3 = 'Темперамент - средний темперамент.'
    elif sum_num3 > 5:
        text3 = 'Темпераиент - сильная харизма.'

    text = f'{text1} \n{text2} \n{text3}'
    return text


def D2(mass_in):
    matrix = baza(mass_in)

    sum_num1 = matrix[1][0] + matrix[1][1] + matrix[1][2]
    sum_num2 = matrix[0][1] + matrix[1][1] + matrix[2][1]

    text1 = ''
    text2 = ''
    # вводим ответы
    # Семья
    if sum_num1 < 4:
        text1 = 'Семья - не стремитесь к браку и рождению детей.'
    elif sum_num1 < 6:
        text1 = 'Семья - для вас важна семья.'
    elif sum_num1 > 5:
        text1 = 'Семья - для вас очень важна семья.'

    # Финансы
    if sum_num2 < 3:
        text2 = 'Финансы - слабо выражено умение рационально пользоваться деньгами.'
    elif sum_num2 == 3:
        text2 = 'Финансы - вы находитесь на грани экономии и расточительства.'
    elif sum_num2 > 3:
        text2 = 'Финансы - талант зарабатывать, иногда скупость.'

    text = f'{text1} \n{text2}'
    return text


def D3(mass_in):
    matrix = baza(mass_in)

    sum_num1 = matrix[0][0] + matrix[0][1] + matrix[0][2]
    sum_num2 = matrix[0][2] + matrix[1][2] + matrix[2][2]
    sum_num3 = matrix[2][0] + matrix[2][1] + matrix[2][2]

    text1 = ''
    text2 = ''
    text3 = ''

    # вводим ответы
    # Цель
    if sum_num1 < 4:
        text1 = 'Цель - сниженные амбиции.'
    elif sum_num1 < 6:
        text1 = 'Цель - благоприятные амбиции.'
    elif sum_num1 > 6:
        text1 = 'Цель - стремление достичь желаемого любыми путями.'

    # Талант
    if sum_num2 < 4:
        text2 = 'Талант - нет природного потенциала, но все возможности у вас в руках!'
    elif sum_num2 > 3:
        text2 = 'Талант - наличие природного потенциала.'

    # Привычки
    if sum_num3 < 4:
        text3 = 'Привычки - легко приспосабливаетесь к новым условиям.'
    elif sum_num3 > 3:
        text3 = 'Привычки - стараетесь не менять своих привычек.'

    text = f'{text1} \n{text2} \n{text3}'
    return text


def baza(mass_in):
    mass2 = mass_in[:]
    p1 = 0
    for i in range(8):
        p1 += int(mass2[i])

    if len(str(p1)) > 1:
        p2 = int((str(p1))[:1]) + int((str(p1))[1:])
    elif len(str(p1)) == 1:
        p2 = p1

    p3 = abs(p1 - (int(mass2[0]) * 2))

    if len(str(p3)) > 1:
        p4 = int((str(p3))[:1]) + int((str(p3))[1:])
    elif len(str(p3)) == 1:
        p4 = p3

    # добавление всего в массив
    if len(str(p1)) == 1:
        mass2.append(int(p1))
    elif len(str(p1)) == 2:
        mass2.append(int((str(p1))[:1]))
        mass2.append(int((str(p1))[1:]))

    if len(str(p2)) == 1:
        mass2.append(int(p2))
    elif len(str(p2)) == 2:
        mass2.append(int((str(p2))[:1]))
        mass2.append(int((str(p2))[1:]))

    if len(str(p3)) == 1:
        mass2.append(int(p3))
    elif len(str(p3)) == 2:
        mass2.append(int((str(p3))[:1]))
        mass2.append(int((str(p3))[1:]))

    if len(str(p4)) == 1:
        mass2.append(int(p4))
    elif len(str(p4)) == 2:
        mass2.append(int((str(p4))[:1]))
        mass2.append(int((str(p4))[1:]))

    # создаём матрицу и вписываем значения:
    matrix = [[0] * 3 for _ in range(3)]
    for i in mass2:
        if i == 1:
            matrix[0][0] += 1
        elif i == 2:
            matrix[1][0] += 1
        elif i == 3:
            matrix[2][0] += 1
        elif i == 4:
            matrix[0][1] += 1
        elif i == 5:
            matrix[1][1] += 1
        elif i == 6:
            matrix[2][1] += 1
        elif i == 7:
            matrix[0][2] += 1
        elif i == 8:
            matrix[1][2] += 1
        elif i == 9:
            matrix[2][2] += 1

    return matrix


def get_email_data_list(email_data_str: str) -> list:
    email_data_list = email_data_str.split("@")
    return email_data_list


def send_email(access_token: str, sender_email_name: str, sender_email: str,
               recipient_email: str, subject: str, message: str) -> bool:
    try:
        just_a_str = f"user={sender_email}\x01auth=Bearer {access_token}\x01\x01"
        xoauth2_token = base64.b64encode(bytes(just_a_str, 'utf-8')).decode('utf-8')

        sender_email_login = get_email_data_list(sender_email)[0]
        sender_email_domain = get_email_data_list(sender_email)[1]
        recipient_email_login = get_email_data_list(recipient_email)[0]
        recipient_email_domain = get_email_data_list(recipient_email)[1]

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = Address(sender_email_name, sender_email_login, sender_email_domain)
        # recipient_email_name,
        msg['To'] = Address('', recipient_email_login, recipient_email_domain)
        msg.set_content(message, 'html')

        smtp = smtplib.SMTP_SSL(host='smtp.yandex.ru', port=465)
        smtp.connect(host='smtp.yandex.ru', port=465)
        smtp.docmd("AUTH", f"XOAUTH2 {xoauth2_token}")
        smtp.sendmail(sender_email, recipient_email, msg.as_string())
        smtp.quit()
    except Exception:
        return False

    return True


def get_sender_email_data(access_token: str) -> list:
    login_info_url = "https://login.yandex.ru/info?oauth_token={}"

    try:
        response = requests.get(login_info_url.format(access_token))
        user_data = response.json()
        sender_name = user_data["display_name"]
        sender_email = user_data["default_email"]
    except Exception:
        return []

    return [sender_name, sender_email]


def make_letter(mass_in):
    matrix = baza(mass_in)

    if matrix[0][0] == 0:
        text1 = 'Характер - слабо выражен. '
    elif matrix[0][0] == 1:
        text1 = 'Характер - мягкий, сниженная воля и ответственность. '
    elif matrix[0][0] == 2:
        text1 = 'Характер - деликатный, вежливый. Приятный в общении человек, который любит похвалу и знаки внимания. '
    elif matrix[0][0] == 3:
        text1 = 'Характер - умеренный, умеете быстро подстраиваться под обстоятельства. '
    elif matrix[0][0] == 4:
        text1 = 'Характер - характер прирожденного лидера, который способен руководить и брать на себя инициативу. '
    elif matrix[0][0] == 5:
        text1 = 'Характер - характер диктатора, который настолько стремится к своим целям, что не замечает никаких препятствий. '
    elif matrix[0][0] == 6:
        text1 = 'Характер - перегруженный характер, завышенные амбиции не реализуются из-за низкой целеустремленности. '
    else:
        text1 = 'Характер - человек все контролирует, но сам избегает ответственности. '

    # Энергия
    if matrix[1][0] == 0:
        text2 = 'Энергия - дефицит энергии, постоянное ощущение усталости, нехватка времени. '
    elif matrix[1][0] == 1:
        text2 = 'Энергия - постоянная суета, спешка, лень, прокрастинация, напрасная трата сил. '
    elif matrix[1][0] == 2:
        text2 = 'Энергия - активность, энергичность, общительная личность, которая все успевает и имеет широкий круг интересов. '
    else:
        text2 = 'Энергия - безграничный запас энергии, что позволяет быстро решать несколько задач сразу и оказывать влияние на людей. '

    # Здоровье
    if matrix[0][1] == 0:
        text4 = 'Здоровье - здоровье далеко от идеального, могут быть хронические заболевания, сниженный иммунитет, плохое зрение. '
    elif matrix[0][1] == 1:
        text4 = 'Здоровье - здоровый, устойчивый к болезням организм, и привлекательность. '
    elif matrix[0][1] == 2:
        text4 = 'Здоровье - скорее всего профессиональный спортсмен, выносливы и способны быстро восстанавливаться. '
    else:
        text4 = 'Здоровье - большая физическая сила, которая может переходить в агрессию. '

    if matrix[2][0] == 0:
        text3 = 'Интерес - талант в творчестве. '
    elif matrix[2][0] == 1:
        text3 = 'Интерес - сложно выбрать одно направление, поэтому постоянно мечетесь между разными сферами. '
    elif matrix[2][0] == 2:
        text3 = 'Интерес - ярко выраженное стремление к получению знаний, особенно в области математики, техники, аналитики. '
    else:
        text3 = 'Интерес - есть способности для больших научных открытий, а также талант генерировать оригинальные идеи. '

    # Логика
    if matrix[1][1] == 0:
        text5 = 'Логика - мечтатель, который любит строить воздушные замки, но не умеет планировать. '
    elif matrix[1][1] == 1:
        text5 = 'Логика - способность мыслить логически и редко допускаете ошибки в своих расчетах. '
    elif matrix[1][1] == 2:
        text5 = 'Логика - острый ум и тонкое чутьё, способности стратега и аналитика. '
    else:
        text5 = 'Логика - перегруженная логика, при которой человека могут одолевать навязчивые мысли, перфекционизм '

    # Ум
    if matrix[2][2] == 0:
        text9 = 'Ум - слабая память, сложности в изложении своих мыслей. '
    elif matrix[2][2] == 1:
        text9 = 'Ум - способность запомнить лишь те сведения, которые требуются ему ежедневно. '
    elif matrix[2][2] == 2:
        text9 = 'Ум - способность помнить все детали. '
    else:
        text9 = 'Ум - мощный интеллектуальный потенциал, который в негативе реализуется как злопамятность. '

        # Труд
    if matrix[2][1] == 0:
        text6 = 'Труд - человек не любит заниматься монотонной ручной работой, а предпочитает зарабатывать своим умом. '
    elif matrix[2][1] == 1:
        text6 = 'Труд - есть способности шить, готовить, мастерить, но результат во многом зависит от запаса энергии. '
    elif matrix[2][1] == 2:
        text6 = 'Труд - мастер с золотыми руками, его профессия обычно связана с ремеслом. '
    else:
        text6 = 'Труд - склонности к оккультизму, умение управлять, манипулировать людьми. '

    # Удача
    if matrix[0][2] == 0:
        text7 = 'Удача - человек ничего не получает просто так, но это не означает глобальное невезение. '
    elif matrix[0][2] == 1:
        text7 = 'Удача - в жизни этого человека нередко случаются удачные совпадения. '
    elif matrix[0][2] == 2:
        text7 = 'Удача - постоянное присутствие удачи и защиту высших сил. '
    else:
        text7 = 'Удача - практически незамедлительно реализуются любые мысли, то есть и мечты, и страхи. '

    # Долг
    if matrix[1][2] == 0:
        text8 = 'Долг - человек склонен больше принимать, чем отдавать, ставить на первый план свои интересы, вести себя эгоистично. '
    elif matrix[1][2] == 1:
        text8 = 'Долг - способность ответственно выполнять работу, но в личной жизни старается избегать обязательств. '
    elif matrix[1][2] == 2:
        text8 = 'Долг - человек заботлив, добр, терпим, щедр, честен. '
    else:
        text8 = 'Долг - сильный контроль, гиперопека, религиозность. '

    sum_num14 = matrix[0][0] + matrix[1][0] + matrix[2][0]
    sum_num17 = matrix[0][0] + matrix[1][1] + matrix[2][2]
    sum_num18 = matrix[2][0] + matrix[1][1] + matrix[0][2]

    # вводим ответы
    # Самооценка
    if sum_num14 < 4:
        text14 = 'Самооценка занижена.'
    elif sum_num14 < 6:
        text14 = 'Самооценка нормальная, здоровая.'
    elif sum_num14 > 5:
        text14 = 'Самооценка завышена.'

    # Духовность
    if sum_num17 < 2:
        text17 = 'Духовность - не придерживаетесь религии.'
    elif sum_num17 < 4:
        text17 = 'Духовность - относитесь нейтрально к религии.'
    elif sum_num17 > 3:
        text17 = 'Духовность - придерживаетесь религии.'

    # Темперамент
    if sum_num18 < 4:
        text18 = 'Темперамент - слабо выражен темперамент.'
    elif sum_num18 < 6:
        text18 = 'Темперамент - средний темперамент.'
    elif sum_num18 > 5:
        text18 = 'Темпераиент - сильная харизма.'

    sum_num12 = matrix[1][0] + matrix[1][1] + matrix[1][2]
    sum_num15 = matrix[0][1] + matrix[1][1] + matrix[2][1]

    # Семья
    if sum_num12 < 4:
        text12 = 'Семья - не стремитесь к браку и рождению детей.'
    elif sum_num12 < 6:
        text12 = 'Семья - для вас важна семья.'
    elif sum_num12 > 5:
        text12 = 'Семья - для вас очень важна семья.'

    # Финансы
    if sum_num15 < 3:
        text15 = 'Финансы - слабо выражено умение рационально пользоваться деньгами.'
    elif sum_num15 == 3:
        text15 = 'Финансы - вы находитесь на грани экономии и расточительства.'
    elif sum_num15 > 3:
        text15 = 'Финансы - талант зарабатывать, иногда скупость.'

    sum_num11 = matrix[0][0] + matrix[0][1] + matrix[0][2]
    sum_num16 = matrix[0][2] + matrix[1][2] + matrix[2][2]
    sum_num13 = matrix[2][0] + matrix[2][1] + matrix[2][2]

    if sum_num11 < 4:
        text11 = 'Цель - сниженные амбиции.'
    elif sum_num11 <= 6:
        text11 = 'Цель - благоприятные амбиции.'
    elif sum_num11 > 6:
        text11 = 'Цель - стремление достичь желаемого любыми путями.'

    # Талант
    if sum_num16 < 4:
        text16 = 'Талант - нет природного потенциала, но все возможности у вас в руках!'
    elif sum_num16 > 3:
        text16 = 'Талант - наличие природного потенциала.'

    # Привычки
    if sum_num13 < 4:
        text13 = 'Привычки - легко приспосабливаетесь к новым условиям.'
    elif sum_num13 > 3:
        text13 = 'Привычки - стараетесь не менять своих привычек.'

    text = f'''
    <html>
    <head></head>
    <body>
        <p><h3>Расшифровка "Квадрата Пифагора":</h3></p>
        <p>
        {format_response(text1)}<br>
        {format_response(text2)}<br>
        {format_response(text3)}<br>
        {format_response(text4)}<br>
        {format_response(text5)}<br>
        {format_response(text6)}<br>
        {format_response(text7)}<br>
        {format_response(text8)}<br>
        {format_response(text9)}<br>
        {format_response(text11)}<br>
        {format_response(text12)}<br>
        {format_response(text13)}<br>
        {format_response(text14)}<br>
        {format_response(text15)}<br>
        {format_response(text16)}<br>
        {format_response(text17)}<br>
        {format_response(text18)}</p>
    </body>
    </html>
    '''

    return text


def format_response(txt: str) -> str:
    p = txt.find(' ')
    if p > 0:
        return '<b>' + txt[:p] + '</b>' + txt[p:]
    else:
        return txt


def help_get():
    return 'Чтобы получить рассчёт "Квадрата Пифагора" назови дату Рождения, например 6 августа 1990 года.\n При желании ты сможешь отправить письмо с расшифровкой на почту.'
