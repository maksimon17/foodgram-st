Здравствуйте, прошу прощения за то что сдал пустой проект - почему-то не "запушился" он на GitHub, но сейчас я все проверил, порядок. Также я слышал от других студентов что бывают ошибки с Postman (у студента все тесты проходит, а у вас нет) поэтому приложу сюда скриншоты пройденного теста в Postman. + в папку (...foodgram-st\postman_collection) добавил файл (выгрузку) из Postman, чтобы вы могли проверить, если будут какие-то сомнения.
**ДОПОЛНЯЮ:** 
/1 ревью/ Исправил ваши ошибки и провел тесты постман (также, обновил файл в папке ...foodgram-st\postman_collection).
**Новый** скриншот с тестами:

![Снимок экрана 2025-07-04 235824](https://github.com/user-attachments/assets/d8d66b9b-5468-4f7b-9edc-b78696d184a7)

---
# **Foodgram — Продуктовый помощник**

**Foodgram** — веб-приложение для обмена рецептами, подписки на авторов и создания списков покупок. Пользователи могут публиковать рецепты, добавлять их в избранное и автоматически формировать список необходимых продуктов.

---

##  **Как запустить проект**

### ** Клонируйте репозиторий**
```sh
git clone https://github.com/maksimon17/foodgram.git
cd foodgram-st/infra
```

### ** Создайте файл `.env`**
В корне директории `infra/` создайте файл `.env` по примеру `.env.example`

### ** Запустите Docker**
```sh
docker-compose up -d --build
```

### ** Выполните миграции**
```sh
docker-compose exec backend python manage.py migrate
```

### ** Заполните базу ингредиентами**
```sh
docker-compose exec backend python manage.py load_data
```

### ** Создайте суперпользователя (админ)**
```sh
docker-compose exec backend python manage.py createsuperuser
```

После выполнения этих шагов приложение будет доступно по адресу **[http://localhost/](http://localhost/)**.

---

## **Полезные ссылки**

- **Интерфейс веб-приложения** → [http://localhost/](http://localhost/)
- **Спецификация API (Swagger)** → [http://localhost/api/docs/](http://localhost/api/docs/)
- **Панель администратора** → [http://localhost/admin/](http://localhost/admin/)

---

## **Технологии**
- **Backend:** Django, Django REST Framework, PostgreSQL
- **Frontend:** React
- **Развертывание:** Docker, Gunicorn, Nginx
