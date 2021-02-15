import time
import random
import socket
import re
import datetime
import cx_Oracle
from flask import Flask, request, render_template, redirect
app = Flask(__name__, template_folder="templates")


@app.route('/')
def home_page():
    return render_template("index.html")


@app.route('/', methods = ['POST'])
def transaction():
    tran_type = request.form['tran_type']
    tran_code = request.form['tran_code']
    amount = request.form['amount']
    pan = request.form['pan']
    entry_mode = request.form['entry_mode']
    tid = request.form['tid']
    condition = request.form['condition']

    # Special control characters
    DLE = '\x10'
    STX = '\x02'
    ETX = '\x03'
    FS = '\x1C'
    DC3 = '\x13'

    l_num = 2177467201

    # random time for transaction number (auth pres)
    echo = int(round(time.time() * 1000))
    origtime = int(time.time()) + l_num

    # random number for transaction number (auth pres)
    rand = random.randint(100000, 999999)

    # random time for transaction number (pres)
    echo1 = int(round(time.time() * 1000))
    origtime1 = int(time.time()) + l_num

    # random number for transaction number (pres)
    rand1 = random.randint(100000, 999999)


    auth = """
Echo=NEB{echo}{rand}
Ver=1
Product=FIMI
FIMI/Ver=3.5
FIMI/Clerk=SANDPE1
FIMI/Password=SANDPE1
FIMI/TransactionNumber=NEB{echo}{rand}
FIMI/Operation=POSRequest
FIMI/POSRequest/Rq/TranType={tran_type}
FIMI/POSRequest/Rq/TranCode={tran_code}
FIMI/POSRequest/Rq/Amount={amount}
FIMI/POSRequest/Rq/Currency=978
FIMI/POSRequest/Rq/PAN={pan}
FIMI/POSRequest/Rq/Track2={pan}=2512
FIMI/POSRequest/Rq/OrigTime={origtime}
FIMI/POSRequest/Rq/Condition={condition}
FIMI/POSRequest/Rq/EntryMode={entry_mode}
FIMI/POSRequest/Rq/TermName={tid}
FIMI/POSRequest/Rq/RetailerName=104500000000001
FIMI/POSRequest/Rq/DraftCapture=0
FIMI/POSRequest/Rq/FromAcctType=0
FIMI/POSRequest/Rq/MBR=0""".replace('\n', '\x10').format(echo=echo,
                                                         rand=rand,
                                                         tran_type=tran_type,
                                                         amount=amount,
                                                         origtime=origtime,
                                                         pan=pan,
                                                         entry_mode=entry_mode,
                                                         tran_code=tran_code,
                                                         tid=tid,
                                                         condition=condition)
    print(auth)
    length = '%06d' % len(auth)  # What does this do?
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('10.10.251.7', 6007))
    k = STX + length + auth + ETX
    s.send(bytes(k, 'utf-8'))
    data = s.recv(8192)  # authorization response - BYTES
    s.close()
    try:
        data1 = re.search("ExtRespCode=00", str(data)).group(0)
        if data1 == "ExtRespCode=00":
            tran_id = re.search(r'(?<=ThisTranId=).*?(?=FIMI)', str(data)).group(0)
            extpsfields = re.search(r'(?<=ExtPSFields=).*?(?=FIMI/POSRequest/Rp/ExtRRN=)', str(data)).group(0)
            extrrn = re.search(r'(?<=ExtRRN=).*?(?=FIMI/POSRequest/Rp/ExtRespCode=)', str(data)).group(0)
            approval_code = re.search(r'(?<=ApprovalCode=).*?(?=FIMI/POSRequest/Rp/AuthRespCode=)', str(data)).group(0)

            extpsfields = extpsfields.replace('\\x1c', FS)
            extpsfields = extpsfields.replace('\\x13', DC3)
            extpsfields = extpsfields.replace('\\x10', DLE)
            approval_code = approval_code.replace('\\x10', '')
            extrrn = extrrn.replace('\\x10', '')
            
            pres = """
Echo=NEB{echo}{rand}
Ver=1
Product=FIMI
FIMI/Ver=3.5
FIMI/Clerk=SANDPE1
FIMI/Password=SANDPE1
FIMI/TransactionNumber=NEB{echo}{rand}
FIMI/Operation=POSRequest
FIMI/POSRequest/Rq/TranType=220
FIMI/POSRequest/Rq/TranCode={tran_code}
FIMI/POSRequest/Rq/Amount={amount}
FIMI/POSRequest/Rq/Currency=978
FIMI/POSRequest/Rq/PAN={pan}
FIMI/POSRequest/Rq/Track2={pan}=2512
FIMI/POSRequest/Rq/OrigTime={origtime}
FIMI/POSRequest/Rq/Condition=87
FIMI/POSRequest/Rq/EntryMode={entry_mode}
FIMI/POSRequest/Rq/TermName={tid}
FIMI/POSRequest/Rq/RetailerName=104500000000001
FIMI/POSRequest/Rq/DraftCapture=2
FIMI/POSRequest/Rq/FromAcctType=0
FIMI/POSRequest/Rq/ApprovalCode={approval_code}
FIMI/POSRequest/Rq/ExtPSFields={extpsfields}
FIMI/POSRequest/Rq/ExtRRN={extrrn}
FIMI/POSRequest/Rq/MBR=0""".replace('\n', '\x10').format(echo=echo1,
                                                         rand=rand1,
                                                         amount=amount,
                                                         origtime=origtime1,
                                                         extpsfields=extpsfields,
                                                         extrrn=extrrn,
                                                         approval_code=approval_code,
                                                         tid=tid,
                                                         pan=pan,
                                                         entry_mode=entry_mode,
                                                         tran_code=tran_code)
            # print(pres)
##            if str(condition) in ('81', '82'):
##                if pan[0] == '4':
##                    pres += '\x10' + "FIMI/POSRequest/Rq/CAVV=0700010024799300000000000000000000000000"
            length = '%06d' % len(pres)  # What does this do?
            pres_req = STX + length + pres + ETX
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('10.10.251.7', 6007))
            s.send(bytes(pres_req, 'utf-8'))
            pres_response = s.recv(1024)  # presentment response
            s.close()
            print(pres_response)
            return render_template("index.html", embed="Authorization approved! Transaction ID: " + tran_id.replace('\\x10', ''),
                                   membed="Presentment approved! Transaction ID: " + re.search(r"(?<=ThisTranId=).*", str(pres_response)).group(0).replace("\\x03'", ""))
    except:
        try:
            decline_reason = re.search("(?<=DeclineReason=).*(?=FIMI)", str(data)).group(0)
            return render_template("index.html", embed="Decline reason: " + decline_reason.replace('\\x10', ''))
        except:
            decline_reason = re.search(r'(?<=AuthRespCode=).*?(?=FIMI)', str(data)).group(0)
            return render_template("index.html", embed="Decline reason: " + decline_reason.replace('\\x10', ''))


@app.route('/luhn')
def luhn():
    return render_template("luhn.html")


@app.route('/luhn', methods=['POST'])
def luhn_check():
    pan = request.form['pan']
    if len(pan) == 16:
        a = []
        b = pan
        for i in range(len(pan)):
            a.append(int(b[i]))
        c = a[0::2]
        c1 = [i * 2 for i in c]
        for i in range(len(c1)):
            if c1[i] > 9:
                c1[i] -= 9
        d = a[1::2]
        a1 = c1 + d
        e = sum(a1)
        if e % 10 == 0:
            return render_template("luhn.html", luhn="PAN is valid.")

        else:
            k = e
            while e % 10 != 0:
                e += 1
            sum1 = e - k + int(b[-1])
            if sum1 > 9:
                sum1 = str(sum1)[1]
            return render_template("luhn.html", luhn="Last digit should be {}.".format(sum1))

    else:
        return render_template("luhn.html", luhn="PAN not entered!")


if __name__ == '__main__':
    app.run()
