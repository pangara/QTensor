from qtensor.tools import mpi
from qtensor.tools import maxcut
from qtensor.tools import lazy_import
from qtensor.tools import benchmarking
from qtensor.tools.lib_interface import qiskit_circuit
from qtensor.tools.lazy_import import LasyModule

#-- gamma, beta for optimized bethe lattice
# val: QAOA approximation value expectation
# angles: gamma, beta = angles[:p], angles[p:]. ranged from 0 to pi

BETHE_QAOA_VALUES_nonsmooth = {"1": {"val": 0.69245005020442, "angles": [1.263056315424361, 1.178096198604872]},
                     "2": {"val": 0.7559063097485101, "angles": [1.32685265, 2.69271336, 1.01604087, 1.27853893]},
                     "3": {"val": 0.792315514902161, "angles": [-0.20893916, -0.39607388, -0.46616474,  0.60032889,  0.45241986, 0.23511412]},
                     "4": {"val": 0.8167299894216052, "angles": [-0.20359203, -0.38936673, -0.48893051, -0.57195008,  0.59413038, 0.44061878,  0.31250151,  0.16312574]},
                     "5": {"val": 0.8363793482380077, "angles": [0.1796198 , 1.92385142, 1.98188023, 0.501994  , 2.14758096, 0.93905843, 0.52261397, 1.18051168, 1.29460152, 1.72013775]},
                     "6": {"val": 0.8498938819897202, "angles": [0.16573358, 1.89337448, 3.50724417, 0.41837306, 2.0756843 , 2.13420824, 0.93509952, 0.53407238, 2.0337603 , 0.35987601, 1.31228924, 0.13888416]},
                     "7": {"val": 0.859619124021074, "angles": [-0.15377355, -0.31005903, -0.3503048 , -0.38206462, -0.43283877, -0.51775878, -0.56291815,  0.64806401,  0.55839915,  0.5007673 , 0.45132269,  0.33452177,  0.23544465,  0.12965313]},
                     "8": {"val": 0.8672299758118122, "angles": [-0.15110518, -0.30065302, -0.32989605, -0.35575995, -0.38652352, -0.43401209, -0.51191577, -0.55226104,  0.65650754,  0.56238557, 0.49776919,  0.46996502,  0.41361734,  0.31031851,  0.22814776, 0.12058734]},
                     "9": {"val": 0.8723780358122347, "angles": [-0.1397006 , -0.28306662, -0.3156113 , -0.33966626, -0.36312033, -0.38402821, -0.437261  , -0.51873546, -0.55899333,  0.65447387, 0.56186397,  0.5090114 ,  0.48677629,  0.45143509,  0.40321108, 0.30473032,  0.21983296,  0.11718174]},
                     "10": {"val": 0.8785275447411593, "angles": [-0.13335818, -0.27241135, -0.30499051, -0.32813004, -0.34785418, -0.3643787 , -0.38693879, -0.44105569, -0.5219005 , -0.55762961, 0.65558354,  0.56318149,  0.51388817,  0.49558422,  0.46889487, 0.43574328,  0.38847067,  0.29117619,  0.21050905,  0.11238794]},
                     "11": {"val": 0.8828425408436951, "angles": [-0.1286437 , -0.26402029, -0.29588548, -0.31984575, -0.33860281, -0.35103073, -0.36851213, -0.38765375, -0.44177937, -0.52348513, -0.55761886,  0.65643879,  0.56334713,  0.51630143,  0.50366825, 0.481823  ,  0.45601256,  0.42143463,  0.37077327,  0.27645017, 0.20094698,  0.1072507 ]},
                     "12": {"val": -10, "angles": []}
                    }


BETHE_QAOA_VALUES = {
    '1': {'val': 0.6924500474008557, 'angles': [-0.307766814546916, 0.3926720292447629]},
    '2': {'val': 0.7559062918257108, 'angles': [-0.24385486635492434, -0.4489938478112711, 0.5550603400685824, 0.29250781484335187]},
    '3': {'val': 0.7923980072764281, 'angles': [-0.21104204095116305, -0.3992063770279206, -0.4685443982836962, 0.608757260014991, 0.45927530900125874, 0.23539562255067184]},
    '4': {'val': 0.8168758698205445, 'angles': [-0.2043819225688009, -0.3902924821151849, -0.4938640601617414, -0.5781568377134791, 0.5995654665076653, 0.4344182507567688, 0.29695001489559947, 0.15906683733146543]},
    '5': {'val': 0.8363791264990517, 'angles': [-0.1797947034873593, -0.35328630130143646, -0.41127827382980825, -0.5023774474367088, -0.5771372909322555, 0.6318520293950315, 0.5226524412470716, 0.3897420609614237, 0.2754121638618102, 0.1491700495831238]},
    '6': {'val': 0.8498936745383119, 'angles': [-0.1655209049103754, -0.32251550305268045, -0.3653884580896713, -0.418291572316067, -0.5045817702217613, -0.5630501866191908, 0.6355589295314058, 0.5339629402370255, 0.4631092335134802, 0.3602554466252171, 0.25915232549960054, 0.13902573609703753]},
    '7': {'val': 0.8597933410827674, 'angles': [-0.15504489811131092, -0.3091094095044593, -0.34512392591096075, -0.3756110389160168, -0.4295426273729618, -0.5101950145162104, -0.5610331253443376, 0.6481402507440225, 0.553924977795485, 0.489883395749668, 0.4450177185381082, 0.3405836917027854, 0.2438269283195185, 0.1306345706291833]},
    '8': {'val': 0.8674066482812723, 'angles': [-0.14730289199922858, -0.2933927781919967, -0.32720506693028156, -0.3539642915647208, -0.3822871024028353, -0.4321251207714487, -0.5128328314478199, -0.5581436167585954, 0.6491604649814701, 0.5546799488534804, 0.5003222457916596, 0.4686938845614677, 0.41960894909047436, 0.31891713167388375, 0.23132378988234067, 0.12290392279079686]},
    '9': {'val': 0.8735215640022997, 'angles': [-0.1397005962416459, -0.2830666224747596, -0.3156112958891017, -0.33966625947416645, -0.3631203253023906, -0.3840282096025343, -0.4372610025177596, -0.5187354607066378, -0.5589933250628616, 0.6544738691800278, 0.5618639663372907, 0.5090114025125145, 0.4867762872507141, 0.4514350922540272, 0.40321108228165636, 0.30473032103041725, 0.2198329630539531, 0.11718174267088216]},
    '10': {'val': 0.8785275447411593, 'angles': [-0.13335818369683203, -0.2724113490532155, -0.30499051226527735, -0.3281300425787347, -0.3478541786297841, -0.36437869876198875, -0.3869387909986254, -0.441055694899821, -0.5219005038762996, -0.5576296121353519, 0.6555835372498169, 0.5631814864780931, 0.5138881653307606, 0.49558421683669446, 0.4688948671814715, 0.4357432798966732, 0.3884706701377942, 0.29117618969626957, 0.21050904544590224, 0.11238794493527438]},
    '11': {'val': 0.8828425408436951, 'angles': [-0.128643700652063, -0.2640202862139436, -0.29588547723456377, -0.3198457456898253, -0.33860280690288763, -0.35103072672950253, -0.3685121284040829, -0.3876537486841057, -0.4417793652271734, -0.523485127715536, -0.5576188582344336, 0.6564387949836022, 0.5633471282117171, 0.5163014280756274, 0.5036682504396424, 0.4818229959468761, 0.45601255796623946, 0.421434626428442, 0.3707732712794268, 0.27645017426067187, 0.20094698054318946, 0.10725070156301893]}
}