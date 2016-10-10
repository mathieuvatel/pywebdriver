# -*- coding: utf-8 -*-
###############################################################################
#
#   Copyright (C) 2014 Akretion (http://www.akretion.com).
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#   @author Sylvain CALADOR <sylvain.calador@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from pywebdriver import app, config, drivers
from flask_cors import cross_origin
from flask import request, jsonify
from base_driver import ThreadDriver, check
import simplejson
import socket
import logging

logger = logging.getLogger(__name__)


class CashlogyAutomaticCashdrawerDriver(ThreadDriver):
    """ Cashlogy Driver class for pywebdriver """
    def __init__(self):
        ThreadDriver.__init__(self)
        self.status = {'status': 'connecting', 'messages': []}
        self.device_name = "Cashlogy automatic cashdrawer"
        self.socket = False

    def get_status(self):
        return self.status

    def set_status(self, status, message=None):
        if status == self.status['status']:
            if message is not None and message != self.status['messages'][-1]:
                self.status['messages'].append(message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

        if status == 'error' and message:
            logger.error('Payment Terminal Error: '+message)
        elif status == 'disconnected' and message:
            logger.warning('Disconnected Terminal: '+message)

    def send_to_cashdrawer(self, msg):
        if (self.socket is not False):
            try:
                BUFFER_SIZE = 1024
#                 answer = "ok"
                self.socket.send(msg)
                answer = self.socket.recv(BUFFER_SIZE)
                logger.debug(answer)
                return answer
            except Exception, e:
                logger.error('Impossible to send to cashdrawer: %s' % str(e))

    def cashlogy_connection_check(self, connection_info):
        '''This function initialize the cashdrawer.
        '''
        if self.socket is False:
            connection_info_dict = simplejson.loads(connection_info)
            assert isinstance(connection_info_dict, dict), \
                'connection_info_dict should be a dict'
            ip_address = connection_info_dict.get('ip_address')
            tcp_port = int(connection_info_dict.get('tcp_port'))
            # TODO: handle this case, maybe pop up or display
            # on the screen like WiFi button
            if not ip_address or not tcp_port:
                logger.warning('Configuration error, please configure '
                               'ip_address and tcp_port.')
                self.set_status('disconnected')
            else:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((ip_address, tcp_port))
                    self.set_status('connected')
                except Exception, e:
                    logger.error('Impossible to connect the cashdrawer: %s' % str(e))
                    self.set_status('disconnected')

    def cashlogy_connection_init(self, connection_info):
        '''This function initialize the cashdrawer.
        '''
        if self.socket is False:
            self.cashlogy_connection_check(connection_info)
        answer = self.send_to_cashdrawer("#I#")
        return answer

    def cashlogy_connection_exit(self):
        '''This function close the connection with the cashdrawer.
        '''
        answer = self.send_to_cashdrawer("#E#")
        return answer

    def display_backoffice(self):
        '''This function display the backoffice on the cashier screen.
        '''
        # All this "1" are active button to be display on the screen
        message = "#G#1#1#1#1#1#1#1#1#1#1#1#1#1#"
        answer = self.send_to_cashdrawer(message)
        return answer

    def transaction_start(self, payment_info):
        '''This function sends the data to the serial/usb port.
        '''
        payment_info_dict = simplejson.loads(payment_info)
        assert isinstance(payment_info_dict, dict), \
            'payment_info_dict should be a dict'
        amount = int(payment_info_dict['amount'] * 100)  # amount is sent in cents to the cashdrawer
        operation_number = payment_info_dict.get('operation_number', '00001')  # Number to be able to track operation
        display_accept_button = payment_info_dict.get('display_accept_button', '0')  # Allow the user to confirm the change given by customer
        screen_on_top = payment_info_dict.get('screen_on_top', '0')  # Put the screen on top
        see_customer_screen = payment_info_dict.get('see_customer_screen', '0')  # Display customer screen
        message = "#C#%s#1#%s#%s#15#15#%s#1#%s#0#0#" % (operation_number,
                                                        amount,
                                                        see_customer_screen,
                                                        display_accept_button,
                                                        screen_on_top)
        answer = self.send_to_cashdrawer(message)
#         answer = "#0:LEVEL#1700#0#0#0#"
        return answer

cashlogy_driver = CashlogyAutomaticCashdrawerDriver()
drivers['cashlogy'] = cashlogy_driver


@app.route(
    '/hw_proxy/automatic_cashdrawer_connection_check',
    methods=['POST', 'GET', 'PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type'])
def automatic_cashdrawer_connection_check():
    app.logger.debug('Cashlogy: Call automatic_cashdrawer_connection_check')
    connection_info = request.json['params']['connection_info']
    app.logger.debug('Cashlogy: connection_info=%s', connection_info)
    cashlogy_driver.push_task('cashlogy_connection_check', connection_info)
    return jsonify(jsonrpc='2.0', result=True)


@app.route(
    '/hw_proxy/automatic_cashdrawer_connection_init',
    methods=['POST', 'GET', 'PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type'])
def automatic_cashdrawer_connection_init():
    app.logger.debug('Cashlogy: Call automatic_cashdrawer_connection_init')
    connection_info = request.json['params']['connection_info']
    app.logger.debug('Cashlogy: connection_info=%s', connection_info)
    cashlogy_driver.push_task('cashlogy_connection_init', connection_info)
    return jsonify(jsonrpc='2.0', result=True)


@app.route(
    '/hw_proxy/automatic_cashdrawer_connection_exit',
    methods=['POST', 'GET', 'PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type'])
def automatic_cashdrawer_connection_exit():
    app.logger.debug('Cashlogy: Call automatic_cashdrawer_connection_exit')
    cashlogy_driver.push_task('cashlogy_connection_exit', {})
    return jsonify(jsonrpc='2.0', result=True)


@app.route(
    '/hw_proxy/automatic_cashdrawer_transaction_start',
    methods=['POST', 'GET', 'PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type'])
def automatic_cashdrawer_transaction_start():
    app.logger.debug('Cashlogy: Call automatic_cashdrawer_transaction_start')
    payment_info = request.json['params']['payment_info']
    app.logger.debug('Cashlogy: payment_info=%s', payment_info)
    answer = {'info': cashlogy_driver.transaction_start(payment_info)}
    return jsonify(jsonrpc='2.0', result=answer)


@app.route(
    '/hw_proxy/automatic_cashdrawer_display_backoffice',
    methods=['POST', 'GET', 'PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type'])
def automatic_cashdrawer_display_backoffice():
    app.logger.debug('Cashlogy: Call automatic_cashdrawer_display_backoffice')
    cashlogy_driver.push_task('display_backoffice', {})
    return jsonify(jsonrpc='2.0', result=True)
