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
        super().__init__(name, ddl, primary_key, default)