# -*- coding: utf-8 -*-
"""
Calibration equations for different cryostat thermometers

@author: akperuht
"""
import numpy as np
import matplotlib.pyplot as plt
import warnings
from time import perf_counter

def calibration_dipstick_old(R,multiplier):
    '''
    Koirankoppi dipstick temperature sensor calibration
    Aki Ruhtinas, 2017
    email: aki.ruhtinas@gmail.com

    Parameters
    ----------
    R : float
        Thermometer resistance
    multiplier : int
        Resistance bridge multiplier to correct resistance to ohms

    Returns
    -------
    T : float
        Temperature in Kelvins

    '''
    R=R*multiplier
    points=[480,500,1603.7310207365606,6976.7051348175764]
    # Low temperature <5 K polynomial fit
    T=0
    if R>points[3]:
        T=-2.45959e-18*R**5+1.07371e-13*R**4-1.86716e-9*R**3+1.62013e-5*R**2-0.0705395*R+128.879
    # Around 15-35 K polynomial fit
    elif points[1]<R and R<points[2]:
        T=6.76502e-18 *R**6-5.62812e-14*R**5+1.99219e-10*R**4-3.87763e-7*R**3+0.000446408*R**2-0.301794*R+112.562
    # Linear approximation to maintain continuity
    elif points[0]<R and R<points[1]:
        T=-0.068789*R+69.9864
    # Base fit to all temperatures
    else:
        T=-1.26323e12*R**(-6)+7.88601e10*R**(-5)-1.8702e9*R**(-4)+2.66201e7*R**(-3)-397237*R**(-2)+17255.7*R**(-1)+2.53409
    return T

def calibration_Ling_old(R,multiplier):
    '''
    Ling dilution refrigerator temperature sensor calibration
    Ari Helenius, 2020
    
    Very small range calibration function

    Parameters
    ----------
    R : float
        Thermometer resistance
    multiplier : int
        Resistance bridge multiplier to correct resistance to ohms

    Returns
    -------
    T : float
        Temperature in Kelvins

    '''
    R = R*multiplier
    return 0.8287 - 1.76454e-4*R + 2.11729e-8*R**2 - 1.57071e-12*R**3 +\
            7.61027e-17*R**4 - 2.4539e-21*R**5 + 5.22219e-26*R**6 -\
            7.04414e-31*R**7 +5.45476e-36*R**8 - 1.84632e-41*R**9
            
         
def calibration_CX1050_AA_14L(R,**kwargs):
    '''
    Calibration function for Cernox  CX-1050-AA-1.4L sensor
    Serial Number: X105321

    Parameters
    ----------
    R : float
        Thermometer resistance
    **kwargs : 
        'multip', resistance multiplier

    Returns
    -------
    T : TYPE
        DESCRIPTION.

    '''
    # Correct resistance with multiplier if necessary
    multip = 1
    if 'multip' in kwargs:
        multip = kwargs['multip']
    R = R*multip
    
    # Low temperature coefficients, useful range of fit: 
    # 1.40 K to 14.3 K
    # 9825 ohms to 689.3 ohms
    coef_low = [5.527867,  
                -6.379248,
                2.855709, 
                -1.065175,
                0.334348,
                -0.084377,
                0.013947,
                0.000599,
                -0.001649,
                0.001212,
                ]
    ZL_low = 2.79894969622
    ZU_low = 4.13119755741
    
    
    
    # Middle temperature coefficients, useful range of fit:
    # 14.3 K to 80.3 K
    # 689.3 ohms to 189.3 ohms 
    coef_middle = [43.034893,
                    -38.016846,
                    8.162617, 
                    -0.935864,
                    0.093585,
                    -0.003306,
                    -0.006104,
                    ]
    ZL_middle = 2.23461882459 
    ZU_middle = 2.88553993198
    
    
    # High temperature coefficients, useful range of fit:
    # 80.3 K to 325 K
    # 189.3 ohms to 54.31 ohms
    coef_high = [177.551522, 
                -126.721728,
                22.066582,  
                -3.115138,  
                0.595049,   
                -0.112115,  
                0.015706,   
                ]
    ZL_high = 1.72880129581
    ZU_high = 2.3242938345
    
    T = 0
    if R>= 9825:
        T = Chebyshev(R,coef_low,ZU_low,ZL_low)
        warnings.warn("Warning: Temperature below calibrated range")
    elif R<9825 and R>=689.3:
        T = Chebyshev(R,coef_low,ZU_low,ZL_low)
    elif R<689.3 and R>=189.3:
        T = Chebyshev(R,coef_middle,ZU_middle,ZL_middle)
    elif R<189.3 and R>=54.31:
        T = Chebyshev(R,coef_high,ZU_high,ZL_high)
    else:
        T = Chebyshev(R,coef_high,ZU_high,ZL_high)
        warnings.warn("Warning: Temperature above calibrated range")
    return T
         

def calibration_dipstick_new(R,multip = 1):
    '''
    Calibration function for Koirankoppi dipstick temperature sensor
    
    Slow code that is here for backwards compatibility
    
    Calibrated January 2022 by Aki Ruhtinas
    email: aki.ruhtinas@gmail.com

    Parameters
    ----------
    R : float
        Thermometer resistance
    **kwargs : 
        'multip', resistance multiplier

    Returns
    -------
    T : float
        Calculated temperature

    '''
    # Correct resistance with multiplier
    R = R*multip
    
    # Calibration between 4.2 K and 18.087 K
    # 9816 ohms to 1030.73 ohms
    coef_l = [1.0305706890196387,
            -0.44538638729688446,
            0.038245646079858205,
            0.00040965728900122016,
            -0.0012118796335522266,
            0.00016675566193886398,
            -0.0003134743277859895,
            -4.9862349494365405e-05,
            -0.0002538643045723284,
            2.930529810139165e-05,
            0.00010177604830833634,
            ]
    domain_l = [2.72290035,3.99196185]
    pl = np.polynomial.Chebyshev(coef_l,domain = domain_l, window = [-1,1])
    
    
    # Calibration between 18.087 K - 107.681 K
    # 1030.73 ohms to 143.125 ohms
    coef_m = [1.7681898764629274,
            -0.5246006794490299,
            -0.0009736793484812508,
            0.003478858170366785,
            0.0008144241470007147,
            0.00010086660798327552,
            -0.0002057511678956854,
            -1.0562017354248726e-05,
            0.00021521449198016844,
            -0.0003566476960957493,
            -0.00031293753057890167,
            ]
    domain_m = [1.86381739,3.02540734]
    pm = np.polynomial.Chebyshev(coef_m,domain = domain_m, window = [-1,1])
    
    
    # Calibration between 107.681 K - 295.3 K
    # 143.125 ohms to 45.775 ohms
    coef_h =[2.2479945607783676,
            -0.220244799396414,
            0.0001736586172434195,
            -0.0014264062220913924,
            0.00016439143464969143,
            -0.00015075504768659046,
            -7.754154576623546e-05,
            -0.00011707662585304951,
            -2.3972858842214167e-05,
            -0.00010280191330409421,
            -5.983916339295706e-06,
            ]
    domain_h = [1.66062417,2.16173695]
    ph = np.polynomial.Chebyshev(coef_h,domain = domain_h, window = [-1,1])
    
    T = 0
    if R>= 9816:
        T = 10**pl(np.log10(R))
        #warnings.warn("Warning: Temperature below calibrated range")
    elif R<9816 and R>=1030.73:
        T = 10**pl(np.log10(R))
    elif R<1030.73 and R>=143.125:
        T = 10**pm(np.log10(R))
    elif R<143.125 and R>=45.775:
        T = 10**ph(np.log10(R))
    else:
        T = 10**ph(np.log10(R))
        #warnings.warn("Warning: Temperature above calibrated range")
    # Check that temperature is reasonable, and if not return zero
    if 0<T<400:
        return T
    else:
        return 0


def calibration_dipstick(R):
    '''
    Calibration function for Koirankoppi dipstick temperature sensor.
    Vectorized calculation is much faster than slow variant.
    
    Calibrated January 2022 by Aki Ruhtinas
    email: aki.ruhtinas@gmail.com

    Parameters
    ----------
    R : array(float)
        Thermometer resistance
    Returns
    -------
    T : float
        Calculated temperature

    '''       
    # First clip R to reasonable range
    R = np.clip(R,40,10000)
    # Compute with numpy piecewise function to increase computation speed
    T= np.piecewise(R, [R>=1030.73, (1030.73 > R) & (R>=143.125), R<143.125],
                    [lambda x:10**np.polynomial.Chebyshev(
                                [1.0305706890196387,
                                -0.44538638729688446,
                                0.038245646079858205,
                                0.00040965728900122016,
                                -0.0012118796335522266,
                                0.00016675566193886398,
                                -0.0003134743277859895,
                                -4.9862349494365405e-05,
                                -0.0002538643045723284,
                                2.930529810139165e-05,
                                0.00010177604830833634,
                                ],
                        domain = [2.72290035,3.99196185],
                        window = [-1,1])(np.log10(x)),
                     lambda x: 10**np.polynomial.Chebyshev(
                             [1.7681898764629274,
                             -0.5246006794490299,
                             -0.0009736793484812508,
                             0.003478858170366785,
                             0.0008144241470007147,
                             0.00010086660798327552,
                             -0.0002057511678956854,
                             -1.0562017354248726e-05,
                             0.00021521449198016844,
                             -0.0003566476960957493,
                             -0.00031293753057890167,
                             ],domain = [1.86381739,3.02540734], 
                             window = [-1,1])(np.log10(x)),
                     lambda x:10**np.polynomial.Chebyshev(
                             [2.2479945607783676,
                             -0.220244799396414,
                             0.0001736586172434195,
                             -0.0014264062220913924,
                             0.00016439143464969143,
                             -0.00015075504768659046,
                             -7.754154576623546e-05,
                             -0.00011707662585304951,
                             -2.3972858842214167e-05,
                             -0.00010280191330409421,
                             -5.983916339295706e-06,
                             ],
                             domain = [1.66062417,2.16173695],
                             window = [-1,1])(np.log10(x))]
                    )
    # Make sure values are within reasonable range
    return np.clip(T,4,350)

    

def calibration_Ling(R,multip=1):
    '''
    Better calibration function for Ling made by Aki Ruhtinas. 
    Calibration data measured by Ari Helenius.

    Parameters
    ----------
    R : float
        Thermometer resistance
    **kwargs : 
        'multip', resistance multiplier

    Returns
    -------
    T : float
        Calculated temperature

    '''
    # Correct resistance with multiplier and move to logspace
    R = R*multip
    
    # Calibration between 40 mK and 20K
    coef_ling = [-5.30606160e-01, 
            -1.20610503e+00, 
            3.99019199e-01, 
            -1.75532773e-01,
            1.14216706e-01, 
            -7.73419751e-02, 
            5.40618959e-02, 
            -3.86658100e-02,
            2.85303341e-02,
            -2.16080176e-02, 
            1.63169093e-02,
            -1.29182752e-02,
            1.06184792e-02,
            -7.98300833e-03,
            6.02191244e-03,
            -4.32414907e-03,
            3.41879026e-03, 
            -2.75739361e-03, 
            2.04716983e-03, 
            -1.22720374e-03,
            5.69061400e-04
            ]
    domain_ling = [3.0204657, 5.17597456]
    
    plling = np.polynomial.Chebyshev(coef_ling,domain = domain_ling,window = [-1,1])
    
    return 10**plling(np.log10(R))


def calibration_Kanada(R,multiplier):
    '''
    Wrapper for the Kanada calibration t

    Parameters
    ----------
    R : array or float
        Resistance values to be converted to temperatures

    Returns
    -------
    out : array or float
        Temperature in kelvins

    '''
    out = 0
    if R is None:
        return 0
    if hasattr(R, "__len__"):
        # Correct resistance value in Ohms
        R = np.array(R)*multiplier
        Nr = len(R)
        out = np.zeros(Nr)
        for i in range(Nr):
            out[i] = calibration_Kanada_func(R[i])
    else:
        R = R*multiplier
        out = calibration_Kanada_func(R)
    return out

def calibration_Kanada_lowtemp_2022(R,multiplier):
    '''
    New low temperature calibration for Kanada 1.5K cryostat
    Calibration valid from 15 K to 1.5 K
    Parameters
    ----------
    R : float
        Resistance
    multiplier : float
        Resistance multiplier

    Returns
    -------
    array or float
        Calculated temperature

    '''
    if hasattr(R, "__len__"):
        # Correct resistance value in Ohms
        R = np.array(R)*multiplier
    else:
        R = R*multiplier
        
    coef_0 = [4.837741078001092,
            -5.0386618786563675,
            2.6011253829600314,
            -1.2811240931100099,
            0.6202351699537209,
            -0.290718100542933,
            0.13446140588234368,
            -0.06110535096065962,
            0.027152555428268582,
            -0.010518962898060267,
            0.006875088171212802,
            -0.0025596374495960084
            ]
    domain_0 = [268.137, 1202.448]
    # Define Chebyshev polynomial
    ph = np.polynomial.Chebyshev(coef_0,domain = domain_0, window = [-1,1])
    return ph(R)
           
def calibration_Kanada_func(R):   
    '''
    =======================================================
    Calibration for temperature sensor in Kanada
    Calibration functions 10 degree Chebyshev polynomials
    ========================================================
    '''
    
    '''
    Chebyshev coefficents for different temperature ranges
    '''
    coef_m = [107.6682289065,
              -169.5447785940,
              86.4765089174,
              -28.0981575764,
              6.1235649200,
              -1.9503945254,
              1.0131764357,
              -0.2848764539,
              0.0754777049,
              -0.1217169204,
              0.0183919674
              ]
    ZU_m = 3.0937542834
    ZL_m = 1.5133641164
    
    coef_l = [ 6.8642361690,
              -7.6201321296,
              2.9185476218,
              -0.8169479610,
              0.1364804787,
              0.0336174734,
              -0.0445366064,
              0.0282235691,
              -0.0018566792,
              -0.0065261097,
              0.0115414837
              ]
    ZL_l = 2.3746383841
    ZU_l = 3.0937542834
    
    # Calculation of temperatures using calibration equation
    T=0
    if 287.6046 <= R:
        # Low temperature calibration
        T = Chebyshev(R,coef_l,ZU_l,ZL_l)
    else:
        # Middle temperature calibration
        T = Chebyshev(R,coef_m,ZU_m,ZL_m)
    return T

def calibration_morso(R,multiplier):
    '''
    morso calibration fixed for room temp as of 30.07.2025
    function is from morso_calib_300k_fixed.py
    can be found from nextcloud Toivo\python\
    Calibration of CX-1050-SD-HT thermostat mounted on morsoboard v1
    Toivo Hakanen, 2025
    email: toivohakanen@gmail.com
    datafolders: nextcloud->maasiltagroup->Toivo\data\yyyy-mm-dd-morso-kalibraatio-x
    calibration between 4.18 K and 260 K -> third calibration
    calibration between 260 K and  290 K -> Second calibration
    Parameters
    ----------
    R : float
        Thermometer resistance
    multiplier : int
        Resistance bridge multiplier to correct resistance to ohms

    Returns
    -------
    T : float
        Temperature in Kelvins

    '''

    # Correct resistance with multiplier and move to logspace
    R = R*multiplier
    
     # Calibration between 4.2 K and 20 K
    # domain between 3070.9799999999996 ohms to 626.8690000000003 ohms

    coef_l = [0.9506674308499167,
            -0.35199927764236455,
            0.016258403822749814,
            0.0055715910387260014,
            0.0008861267363886899,
            -0.0005390646317558515,
            0.00046234441088706396,
            -0.00034663919545294743,
            1.8900818521904524e-05,
            -0.0006577629496062799,
            -0.0010153963072063212
            ]
    domain_l = [2.79717679, 3.48727699]
    pl = np.polynomial.Chebyshev(coef_l,domain = domain_l, window = [-1,1])
    
    
    # Calibration between 20 K - 70 K
    # domain between 629.86 to  221.75ohms
    coef_m = [1.57422337136405,
            -0.2644571720191467,
            0.0018751976846375657,
            0.00015485832655411989,
            0.0002687387319480107,
            0.00042994288778457724,
            0.0001854343092784725,
            0.000677677389021527,
            2.7489387520667344e-05,
            -6.839382864240871e-05,
            0.00013297037462381675
            ]
    domain_m = [2.34587734, 2.79924403]
    pm = np.polynomial.Chebyshev(coef_m,domain = domain_m, window = [-1,1])
    
    
    # Calibration between 70 K - 260 K
    # domain between 252.52599 ohms to 64.0478 ohms
    coef_h =[2.105907955347509,
            -0.32561185605929055,
            -0.00452466867832195,
            -0.0041969745056598,
            0.002813068419108741,
            -0.0012856814956658373,
            0.001022107637142309,
            -0.0008692536680943596,
            0.0005275420860334051,
            -0.0007986614863778288,
            0.0004594498328113981,
            ]
    domain_h = [1.80650422, 2.4023061 ]
    ph = np.polynomial.Chebyshev(coef_h,domain = domain_h, window = [-1,1])
    
    #Calibration between 260 K - 293 K
    #Domain between 58.184299999999986 ohm to 73.04270000000002 ohm
    coef_uh=[2.419846561814242,
    -0.05110237731635884,
    -0.00032812984876488935,
    0.00019824559266527853,
    -0.0009580047292876272,
    0.0004420826699351031,
    -0.00031778576498260353,
    9.294972361020348e-05,
    0.0002128491379170427,
    -7.140389360008976e-05,
    -9.114398708705641e-05
    ]
    
    domain_uh = [1.7648058138045555,1.8635768183793173]
    puh = np.polynomial.Chebyshev(coef_uh,domain = domain_uh, window = [-1,1])
    
    T = 0
    if R>= 3071:
        T = 10**pl(np.log10(R))
        warnings.warn("Warning: Temperature below calibrated range")
    elif R<3071 and R>=620.847233906399:#low, crossing point between low and mid, though domain is in 626 for low
        T = 10**pl(np.log10(R))
    elif R<620.847233906399 and R>=224.38862779880543:#mid, mid high has a close crossing near mid domain 221
        T = 10**pm(np.log10(R))
    elif R<224.38862779880543 and R>=64.04780000000001:#high
        T = 10**ph(np.log10(R))
    elif R<64.04780000000001 and R>=58:
        T=10**puh(np.log10(R))
    else:
        T = 10**ph(np.log10(R))#above high
        warnings.warn("Warning: Temperature above calibrated range")
    
    # Check that temperature is reasonable, and if not return zero
    if 0<T<400:
        return T
    else:
        return 0


def Chebyshev(R,coef,ZU,ZL):
    '''
    Chebyshev function for calibration equations

    Parameters
    ----------
    R : float
        Resistance in ohms
    coef : array(float)
        Chebyshev coefficents
    ZU : float
        Chebyshev coefficent
    ZL : float
        Chebyshev coefficent

    Returns
    -------
    T : float
        Temperature in kelvins

    '''
    T = 0
    Z = np.log10(np.longdouble(R))
    k = ((Z-ZL)-(ZU-Z))/(ZU-ZL)
    for i in range(len(coef)):
        T+=np.longdouble(coef[i])*np.cos(i*np.arccos(np.longdouble(k)))
    return T
    
    
if __name__ == '__main__':
    print('Thermometer calibrations')
    
    r = np.linspace(45,10000,10000)
    
    t1 = perf_counter()
    T = calibration_dipstick(r)
    dt1 = perf_counter() - t1
    print(dt1)
    
    t3 = perf_counter()
    T2 = [calibration_dipstick_new(ri,1) for ri in r]
    dt2 = perf_counter() - t3
    print(dt2)
    
    plt.figure()
    plt.semilogx(r,T,'b-')
    plt.semilogx(r,T2,'r-')
    print(dt2/dt1)

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
       
            