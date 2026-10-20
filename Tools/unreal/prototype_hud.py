"""Canvas HUD: readable objectives plus an actual clickable GM panel."""
import unreal as u
from graph_builder import Graph, pin


def build_hud(blueprints, paths):
    bp = blueprints['hud']
    director_class = paths['director']

    def graph(name):
        return Graph(bp, name)

    def state(g, name):
        return g.get(name, g.get('Director'), director_class)

    def label(g, text, x, y, size=1.2):
        g.call('Label', Text=text, X=x, Y=y, Size=size)

    def rect(g, x, y, w, h, color='(R=0.015,G=0.025,B=0.04,A=0.92)'):
        g.engine('HUD', 'DrawRect', RectColor=color, ScreenX=x, ScreenY=y, ScreenW=w, ScreenH=h)

    def concat(g, a, b):
        return g.engine('KismetStringLibrary', 'Concat_StrStr', 'ReturnValue', A=a, B=b)

    def num(g, value):
        return g.engine('KismetStringLibrary', 'Conv_IntToString', 'ReturnValue', InInt=value)

    g = graph('Label')
    g.engine('HUD', 'DrawText', Text=g.param('Text'), TextColor='(R=0.97,G=0.98,B=1.0,A=1.0)',
             ScreenX=g.param('X'), ScreenY=g.param('Y'),
             Scale=g.math('Multiply_DoubleDouble', A=g.param('Size'), B=2.0), bScalePosition=False)

    g = graph('CenteredText')
    scale = g.math('Multiply_DoubleDouble', A=g.param('Size'), B=2.0)
    text_width = g.engine('HUD', 'GetTextSize', 'OutWidth', Text=g.param('Text'), Scale=scale)
    x = g.math('Multiply_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=g.get('ScreenWidth'), B=text_width), B=0.5)
    g.engine('HUD', 'DrawText', Text=g.param('Text'), TextColor=g.param('Color'), ScreenX=x, ScreenY=g.param('Y'), Scale=scale, bScalePosition=False)

    g = graph('GMButton')
    rect(g, 34.0, g.param('Y'), 600.0, 40.0, '(R=0.06,G=0.15,B=0.22,A=1.0)')
    label(g, g.param('Label'), 45.0, g.math('Add_DoubleDouble', A=g.param('Y'), B=10.0), 1.1)
    position = g.engine('KismetMathLibrary', 'MakeVector2D', 'ReturnValue', X=34.0, Y=g.param('Y'))
    size = g.engine('KismetMathLibrary', 'MakeVector2D', 'ReturnValue', X=600.0, Y=40.0)
    g.engine('HUD', 'AddHitBox', Position=position, Size=size, InName=g.param('HitName'), bConsumesInput=True, Priority=5)

    g = graph('DrawGM')
    g.guard(state(g, 'GMOpen'))
    rect(g, 20.0, 220.0, 640.0, 354.0)
    label(g, 'GM / DEBUG CONTROLS  -  F1 CLOSE', 34.0, 234.0, 1.1)
    labels = ['1  DIE / REPEAT LOOP', '2  NEXT STAGE', '3  PREVIOUS STAGE',
              '4  ADD ENEMY', '5  REMOVE ENEMY (NO REWARD)', '6  HACK CAMERA']
    for index, text in enumerate(labels):
        g.call('GMButton', Label=text, Y=264.0 + index * 48, HitName='G' + str(index))

    g = graph('DrawPrototype')
    g.guard(g.valid(g.get('Director')))
    width = g.math('Subtract_DoubleDouble', A=g.get('ScreenWidth'), B=40.0)
    rect(g, 20.0, 18.0, width, 174.0, '(R=0.005,G=0.01,B=0.018,A=0.96)')
    label(g, state(g, 'ObjectiveText'), 34.0, 50.0, 1.15)
    label(g, state(g, 'StatusText'), 34.0, 90.0, 0.95)
    info = concat(g, 'STAGE ', num(g, state(g, 'Stage')))
    info = concat(g, info, concat(g, '     LIVE ENEMIES ', num(g, state(g, 'EnemyCount'))))
    label(g, info, 34.0, 146.0, 0.95)
    footer_y = g.math('Subtract_DoubleDouble', A=g.get('ScreenHeight'), B=62.0)
    rect(g, 20.0, footer_y, width, 44.0)
    label(g, 'WASD move | LMB fire | SHIFT swap | SPACE jump | E interact | Q return | R rewind | F1 GM',
          34.0, g.math('Add_DoubleDouble', A=footer_y, B=13.0), 0.9)
    prompt_y = g.math('Multiply_DoubleDouble', A=g.get('ScreenHeight'), B=0.73)
    def prompt(b):
        text = state(b, 'PromptText')
        tw = b.engine('HUD', 'GetTextSize', 'OutWidth', Text=text, Scale=2.8)
        rect(b, 20.0, b.math('Subtract_DoubleDouble', A=prompt_y, B=10.0),
             b.math('Add_DoubleDouble', A=tw, B=30.0), 52.0,
             '(R=0.005,G=0.01,B=0.018,A=0.97)')
        label(b, text, 34.0, prompt_y, 1.4)
    prompt_length = g.engine('KismetStringLibrary', 'Len', 'ReturnValue', S=state(g, 'PromptText'))
    g.when(g.math('Greater_IntInt', A=prompt_length, B=0), prompt)
    def remote(b):
        rect(b, 20.0, 194.0, 900.0, 42.0, '(R=0.005,G=0.01,B=0.018,A=0.97)')
        label(b, 'REMOTE CAMERA / MOUSE TO PAN / E OR Q TO RETURN', 34.0, 202.0, 1.15)
    g.when(state(g, 'RemoteActive'), remote)
    g.call('DrawGM')
    g.call('DrawCameraPrompt')
    center_x = g.math('Multiply_DoubleDouble', A=g.get('ScreenWidth'), B=0.5)
    center_y = g.math('Multiply_DoubleDouble', A=g.get('ScreenHeight'), B=0.5)
    rect(g, g.math('Subtract_DoubleDouble', A=center_x, B=5.0), center_y, 10.0, 1.5, '(R=0.9,G=1,B=1,A=0.9)')
    rect(g, center_x, g.math('Subtract_DoubleDouble', A=center_y, B=5.0), 1.5, 10.0, '(R=0.9,G=1,B=1,A=0.9)')
    def resetting(b):
        rect(b, 0.0, 0.0, b.get('ScreenWidth'), b.get('ScreenHeight'), '(R=0.005,G=0.01,B=0.015,A=0.98)')
        label(b, 'OFFAIR  /  REWINDING', 120.0, 220.0, 2.0)
        label(b, 'Restoring the stage baseline...', 120.0, 280.0, 1.2)
    g.when(state(g, 'Resetting'), resetting)
    def completed(b):
        rect(b, 40.0, 190.0, b.math('Subtract_DoubleDouble', A=b.get('ScreenWidth'), B=80.0), 220.0)
        label(b, 'OFFAIR  /  LOOP BROKEN', 65.0, 220.0, 2.3)
        label(b, 'Prototype complete. You escaped through the surveillance blind spot.', 65.0, 285.0, 1.2)
        label(b, 'R  /  START AGAIN', 65.0, 345.0, 1.4)
    g.when(state(g, 'Completed'), completed)
    g.call('DrawNarrative')
    length = g.engine('KismetStringLibrary', 'Len', 'ReturnValue', S=state(g, 'FailureText'))
    g.when(g.math('Greater_IntInt', A=length, B=0), lambda b: label(b, state(b, 'FailureText'), 40.0, 180.0, 1.3))

    g = graph('DrawNarrative')
    g.guard(g.valid(g.get('Director')))
    g.guard(g.not_(state(g, 'Resetting')))
    g.guard(g.not_(state(g, 'Completed')))
    width = g.engine('KismetMathLibrary', 'FMin', 'ReturnValue', A=960.0,
                     B=g.math('Subtract_DoubleDouble', A=g.get('ScreenWidth'), B=80.0))
    x = g.math('Multiply_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=g.get('ScreenWidth'), B=width), B=0.5)
    def thought(b):
        y = b.math('Subtract_DoubleDouble', A=b.get('ScreenHeight'), B=170.0)
        rect(b, x, y, width, 88.0, '(R=0.005,G=0.015,B=0.025,A=0.94)')
        b.call('CenteredText', Text=state(b, 'ThoughtText'), Y=b.math('Add_DoubleDouble', A=y, B=18.0),
               Size=1.0, Color='(R=0.35,G=0.85,B=1.0,A=1.0)')
    g.when(g.math('Greater_DoubleDouble', A=state(g, 'ThoughtRemaining'), B=0.0), thought)
    def system_error(b):
        cy = b.math('Multiply_DoubleDouble', A=b.get('ScreenHeight'), B=0.5)
        y = b.math('Subtract_DoubleDouble', A=cy, B=95.0)
        rect(b, x, y, width, 190.0, '(R=0.02,G=0.005,B=0.008,A=0.97)')
        b.call('CenteredText', Text='SYSTEM ERROR', Y=b.math('Add_DoubleDouble', A=y, B=32.0), Size=1.7, Color='(R=1,G=1,B=1,A=1)')
        b.call('CenteredText', Text='Death is required to reset the subject.',
               Y=b.math('Add_DoubleDouble', A=y, B=100.0), Size=1.1, Color='(R=1,G=0.25,B=0.25,A=1)')
    g.when(state(g, 'SystemResetActive'), system_error)

    g = graph('DrawCameraPrompt')
    g.guard(g.valid(g.get('Director')))
    g.guard(state(g, 'CameraPromptVisible'))
    monitor = state(g, 'Monitor')
    g.guard(g.valid(monitor))
    world = g.engine('Actor', 'K2_GetActorLocation', 'ReturnValue', self=monitor)
    anchor = g.math('Add_VectorVector', A=world, B=g.vec(0.0, 0.0, 70.0))
    screen = g.engine('HUD', 'Project', 'ReturnValue', Location=anchor, bClampToZeroPlane=False)
    xyz = g.engine('KismetMathLibrary', 'BreakVector', InVec=screen)
    g.guard(g.math('Greater_DoubleDouble', A=pin(xyz, 'Z', True), B=0.0))
    x = g.math('Subtract_DoubleDouble', A=pin(xyz, 'X', True), B=155.0)
    y = g.math('Subtract_DoubleDouble', A=pin(xyz, 'Y', True), B=38.0)
    rect(g, x, y, 310.0, 38.0, '(R=0.005,G=0.015,B=0.025,A=0.96)')
    label(g, '[E] Hack camera', g.math('Add_DoubleDouble', A=x, B=12.0), g.math('Add_DoubleDouble', A=y, B=8.0), 1.1)

    g = graph('EventGraph')
    g.event('ReceiveBeginPlay')
    director = g.engine('GameplayStatics', 'GetActorOfClass', 'ReturnValue', ActorClass=director_class)
    g.set('Director', g.cast(director, director_class))
    g = graph('EventGraph')
    event = g.event('ReceiveDrawHUD')
    g.set('ScreenWidth', pin(event, 'SizeX', True))
    g.set('ScreenHeight', pin(event, 'SizeY', True))
    g.call('DrawPrototype')
    g = graph('EventGraph')
    g.event('ReceiveTick')
    g.engine('KismetSystemLibrary', 'FlushDebugStrings')
    g = graph('EventGraph')
    event = g.event('ReceiveHitBoxClick')
    g.guard(g.valid(g.get('Director')))
    g.guard(state(g, 'GMOpen'))
    for index in range(6):
        condition = g.math('EqualEqual_NameName', A=pin(event, 'BoxName', True), B='G' + str(index))
        g.when(condition, lambda b, i=index: b.call(director_class + ':GMAction', self=b.get('Director'), Action=i))
