# -*- coding: utf-8 -*-

__author__ = 'Dream'

import aiomysql    # yibu mysql support
import logging     # log support
import asyncio
import pdb

def log(sql, arg=()):
    # use for print execute sql
    logging.info('SQL:%s' % sql)

async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    # create a connection pool
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port'),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop,
    )

async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (await __pool) as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql, args, autocommit=True):
    log(sql)
    with (await __pool) as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

# 构造占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)

# 父域,可被其他域继承
class Field(object):

    # 域的初始化, 包括属性(列)名,属性(列)的类型,是否主键
    # default参数允许orm自己填入缺省值,因此具体的使用请看的具体的类怎么使用
    # 比如User有一个定义在StringField的id,default就用于存储用户的独立id
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    # 用于打印信息,依次为类名(域名),属性类型,属性名
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

# 字符串域
class StringField(Field):

    # ddl("data definition languages"),用于定义数据类型
    # varchar("variable char"), 可变长度的字符串,以下定义中的100表示最长长度,即字符串的可变范围为0~100
    # (char,为不可变长度字符串,会用空格字符补齐)
    def __int__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super(StringField, self).__init__(name, ddl, primary_key, default)

# 整数域
class IntergerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super(IntergerField, self).__init__(name, 'bigint', primary_key, default)

# 布尔域
class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super(BooleanField, self).__init__(name, 'boolean', False, default)

# 浮点数域
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super(FloatField, self).__init__(name, 'real', primary_key, default)

# 文本域
class TextField(Field):
    def __init__(self, name=None, default=None):
        super(TextField, self).__init__(name, 'text', False, default)

# 这是一个元类,它定义了如何来构造一个类,任何定义了__metaclass__属性或指定了metaclass的都会通过元类定义的构造方法构造类
# 任何继承自Model的类,都会自动通过ModelMetaclass扫描映射关系,并存储到自身的类属性
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # cls: 当前准备创建的类对象,相当于self
        # name: 类名,比如User继承自Model,当使用该元类创建User类时,name=User
        # bases: 父类的元组
        # attrs: 属性(方法)的字典,比如User有__table__,id,等,就作为attrs的keys
        # 排除Model类本身,因为Model类主要就是用来被继承的,其不存在与数据库表的映射
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # 以下是针对"Model"的子类的处理,将被用于子类的创建.metaclass将隐式地被继承

        # 获取表名,若没有定义__table__属性,将类名作为表名.此处注意 or 的用法
        tableName = attrs.get("__table__", None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名
        mappings = dict()   # 用字典来储存类属性与数据库表的列的映射关系
        fields = []        # 用于保存除主键外的属性
        primaryKey = None # 用于保存主键

        # 遍历类的属性,找出定义的域(如StringField,字符串域)内的值,建立映射关系
        # k是属性名,v其实是定义域!请看name=StringField(ddl="varchar50")
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mapping: %s ==> %s' % (k, v))
                mappings[k] = v    # 建立映射关系
                if v.primary_key:  # 找到主键
                    if primaryKey: # 若主键已存在,又找到一个主键,将报错,每张表有且仅有一个主键
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k) # 将非主键的属性都加入fields列表中
        if not primaryKey:
            raise RuntimeError('Primary key not found')
        # 从类属性中删除已加入映射字典的键,避免重名
        for k in mappings.keys():
            attrs.pop(k)

        # 将非主键的属性变形,放入escaped_fields中,方便增删改查语句的书写
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mapping__'] = mappings   # 保存属性和列的映射关系
        attrs['__table__'] = tableName    # 保存表名
        attrs['__primary_key__'] = primaryKey # 保存主键
        attrs['__fields__'] = fields      # 保存非主键的属性名

        # 构造默认的select, insert, update, delete语句,使用?作为占位符
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        # 此处利用create_args_string生成的若干个?占位
        # 插入数据时,要指定属性名,并对应的填入属性值(数据库的知识都要忘光了,我这句怎么难看懂- -,惭愧惭愧)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        # 通过主键查找到记录并更新
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        # 通过主键删除
        attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)





