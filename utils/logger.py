#! /usr/bin/env python
# coding=gbk
import logging, os
base_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
log_dir = os.path.join(base_dir, 'log')
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

class Logger:
    def __init__(self, path, clevel=logging.DEBUG, Flevel=logging.DEBUG):
        
        self.logger = logging.getLogger(path)
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(name)s [%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

        # ����CMD��־
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(clevel)
        self.logger.addHandler(sh)

        # �����ļ���־
        fh = logging.FileHandler(os.path.join(log_dir, path + '.log'), mode='w', encoding='gbk')
        fh.setFormatter(fmt)
        fh.setLevel(Flevel)
        self.logger.addHandler(fh)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def cri(self, message):
        self.logger.critical(message)

logger_path = 'venue-logger'
logger = Logger(logger_path)

if __name__ == '__main__':
    logyyx = Logger('yyx.log', logging.ERROR, logging.DEBUG)
    logger.debug('һ��debug��Ϣ')
    logger.info('һ��info��Ϣ')
    logger.warning('һ��warning��Ϣ')
    logger.error('һ��error��Ϣ')
    logger.cri('һ������critical��Ϣ')