using UnrealSharp.Attributes;
using UnrealSharp.CoreUObject;
using UnrealSharp.Engine;

namespace Offair.Managed;

/// <summary>Compact gameplay HUD, single subtitle channel, and a hard-cut OFFAIR title over live play.</summary>
[UClass]
public partial class ARegionHUD : AHUD
{
    [UProperty(PropertyFlags.EditAnywhere)] public partial UFont PlayFont { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UFont SmallPlayFont { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UFont TitleFont { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UTexture2D TitleWordmark { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int CanvasWidth { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int CanvasHeight { get; set; }
    private ARegionLoopDirector? director;
    public override void ReceiveDrawHUD(int sizeX,int sizeY)
    {
        CanvasWidth=sizeX;CanvasHeight=sizeY;
        if(director is null || !SystemLibrary.IsValid(director))
        { UGameplayStatics.GetAllActorsOfClass<ARegionLoopDirector>(out var found);director=found.FirstOrDefault(); }
        if(director is null) return;
        var d=director;
        float s=Math.Clamp(Math.Min(sizeX/1600f,sizeY/900f),.5f,1.6f),m=32*s;
        var white=new FLinearColor(.94f,.97f,1,1);
        var muted=new FLinearColor(.58f,.68f,.74f,1);
        var cyan=new FLinearColor(.28f,.86f,.96f,1);
        var amber=new FLinearColor(1,.74f,.32f,1);
        var red=new FLinearColor(1,.31f,.25f,1);
        var dark=new FLinearColor(.005f,.012f,.02f,.87f);
        if(d.TitleActive && d.Transition==0)
        {
            // Original A wordmark, authored at 6400px; downsample rather than enlarge a font atlas.
            if(TitleWordmark is not null)
            {
                float w=Math.Min(sizeX*.86f,sizeY*.5f*(1600f/300f)),h=w*(300f/1600f);
                DrawTexture(TitleWordmark,(sizeX-w)/2,(sizeY-h)/2,w,h,0,0,1,1,new FLinearColor(1,1,1,1));
            }
            else
            {
                // Readable fallback if the authored UI asset is missing.
                const string title="OFFAIR";
                var font=TitleFont ?? PlayFont;
                const float tracking=18;
                float width=tracking*(title.Length-1),height=0;
                var widths=new List<float>();
                foreach(char c in title)
                {
                    GetTextSize(c.ToString(),out var w,out var h,font,1);
                    widths.Add(w);width+=w;height=Math.Max(height,h);
                }
                float scale=Math.Min(sizeX*.86f/Math.Max(1,width),sizeY*.5f/Math.Max(1,height));
                float x=(sizeX-width*scale)/2,y=(sizeY-height*scale)/2;
                for(int i=0;i<title.Length;i++)
                {
                    DrawText(title[i].ToString(),new FLinearColor(1,1,1,1),x,y,font,scale);
                    x+=(widths[i]+tracking)*scale;
                }
            }
            // Explicitly opened GM remains available for death testing; ordinary HUD stays hidden.
            if(!d.GMOpen) return;
        }
        void Text(string text,float x,float y,FLinearColor color,bool small=false)
            => DrawText(text,color,x,y,small ? SmallPlayFont : PlayFont,s);
        void RightText(string text,float y,FLinearColor color,bool small=true)
        {
            GetTextSize(text,out var width,out _,small ? SmallPlayFont : PlayFont,s);
            Text(text,sizeX-m-width,y,color,small);
        }
        List<string> Wrap(string text,float width,bool small=false)
        {
            var lines=new List<string>();string line="";
            foreach(var word in text.Split(' ',StringSplitOptions.RemoveEmptyEntries))
            {
                var next=line.Length==0 ? word : line+" "+word;
                GetTextSize(next,out var w,out _,small ? SmallPlayFont : PlayFont,s);
                if(w>width && line.Length>0) { lines.Add(line);line=word; } else line=next;
            }
            if(line.Length>0) lines.Add(line);
            return lines;
        }
        void Card(string text,float centerY,FLinearColor color,float maxWidth=850)
        {
            var lines=Wrap(text,Math.Min(maxWidth*s,sizeX-2*m)-32*s,true);
            if(lines.Count==0) return;
            float w=0;
            foreach(var line in lines) { GetTextSize(line,out var lw,out _,SmallPlayFont,s);w=Math.Max(w,lw); }
            float h=(lines.Count*27+16)*s,x=(sizeX-w-32*s)/2,y=centerY-h/2;
            DrawRect(dark,x,y,w+32*s,h);DrawRect(color,x,y,3*s,h);
            for(int i=0;i<lines.Count;i++) Text(lines[i],x+16*s,y+(8+i*27)*s,color,true);
        }
        string objective=d.CheckpointSaved ? (d.VistaPlayed ? "Explore the overlook" : "Step onto the overlook")
            : !d.MemoryExperienced ? "Find the red note" : !d.HasGun ? "Choose a weapon"
            : d.LivingGuards>0 ? $"Clear the room  /  {d.LivingGuards} remaining"
            : !d.HasAccessCard ? "Collect the access card" : !d.CameraLearned ? "Take control of the training camera"
            : d.PuzzleSolved ? "Recover memory B beyond the door" : d.InPuzzleRoom || d.PuzzleRemote ? "Find the pattern. Reproduce it. Submit." : "Enter the Signal Lab";
        if(!d.VistaActive && !d.TitleActive && d.Transition==0)
        {
            float panelW=Math.Min(560*s,sizeX*.48f);
            var objectives=Wrap(objective,panelW-36*s,true);
            bool puzzleHelp=d.InPuzzleRoom && !d.PuzzleSolved && !d.RemoteActive && !d.PuzzleSubmitting;
            var help=puzzleHelp ? Wrap("LMB: Toggle tile   /   E: Console",panelW-36*s,true) : new List<string>();
            float panelH=(44+(objectives.Count+help.Count)*27)*s;
            DrawRect(dark,m,m,panelW,panelH);DrawRect(cyan,m,m,3*s,panelH);
            Text(d.CheckpointSaved ? "MEMORY B  /  SAVED" : d.InPuzzleRoom ? "02  /  SIGNAL LAB" : "OFF AIR  /  CURRENT OBJECTIVE",m+16*s,m+10*s,cyan,true);
            for(int i=0;i<objectives.Count;i++) Text(objectives[i],m+16*s,m+(40+i*27)*s,white,true);
            for(int i=0;i<help.Count;i++) Text(help[i],m+16*s,m+(40+(objectives.Count+i)*27)*s,muted,true);
            RightText("F1  /  GM",m,muted);
            if(d.RemoteActive)
            {
                string hint=d.PuzzleRemote ? (d.PatternAligned ? "SIGNAL ALIGNED" : "FIND THE CYAN SIGNAL") : "TRAINING CAMERA";
                RightText(hint,m+36*s,cyan);
                RightText("MOUSE  Look   E / Q  Return",m+66*s,white);
                float r=22*s,cx=sizeX/2f,cy=sizeY/2f;
                DrawLine(cx-r,cy-r,cx-r/2,cy-r,cyan,s);DrawLine(cx-r,cy-r,cx-r,cy-r/2,cyan,s);
                DrawLine(cx+r,cy+r,cx+r/2,cy+r,cyan,s);DrawLine(cx+r,cy+r,cx+r,cy+r/2,cyan,s);
            }
            else
            {
                DrawRect(white,sizeX/2f-2*s,sizeY/2f-s,4*s,2*s);
                DrawRect(dark,m,sizeY-m-64*s,180*s,64*s);
                Text($"HEALTH  {Math.Ceiling(d.Health)}",m+12*s,sizeY-m-55*s,d.Health<d.MaximumHealth*.25 ? red : white,true);
                DrawRect(muted,m+12*s,sizeY-m-15*s,152*s,3*s);
                DrawRect(cyan,m+12*s,sizeY-m-15*s,152*s*Math.Clamp(d.Health/Math.Max(1,d.MaximumHealth),0,1),3*s);
                if(d.HasGun)
                {
                    string ammo=$"{d.Ammo:00}  /  AMMO";
                    GetTextSize(ammo,out var width,out _,PlayFont,s);
                    float x=sizeX-m-width-24*s;
                    DrawRect(dark,x,sizeY-m-64*s,width+24*s,64*s);
                    Text(ammo,x+12*s,sizeY-m-52*s,white);
                }
            }
            if(!string.IsNullOrEmpty(d.PromptText)) Card(d.PromptText,sizeY*.64f,white);
            else if(!d.MemoryExperienced)
                Text("WASD  Move     SPACE  Jump     E  Interact",m,sizeY-m-104*s,muted,true);
            if(!string.IsNullOrEmpty(d.PuzzleStatus)) Card(d.PuzzleStatus,sizeY*.38f,d.PuzzleSubmitting ? red : cyan);
            if(!string.IsNullOrEmpty(d.NoticeText)) Card(d.NoticeText,sizeY*.27f,cyan);
        }
        if(d.VistaActive)
        {
            // Crop only top/bottom: 16:9 becomes 16:8; wider viewports keep their full width.
            float bar=sizeY/18f;
            DrawRect(new FLinearColor(0,0,0,1),0,0,sizeX,bar);
            DrawRect(new FLinearColor(0,0,0,1),0,sizeY-bar,sizeX,bar);
            Text("MEMORY B SECURED",m,12*s,muted,true);
            RightText("SPACE  Skip view",12*s,white);
        }
        // A single card: host and inner voice never occupy simultaneous subtitle slots.
        if(d.Transition==0 && !d.TitleActive && !string.IsNullOrEmpty(d.SubtitleText))
        {
            float w=Math.Min(940*s,sizeX-2*m),x=(sizeX-w)/2;
            var lines=Wrap(d.SubtitleText,w-48*s);
            float h=(48+lines.Count*34)*s,y=sizeY-122*s-h;
            var color=d.SubtitleSpeaker==1 ? amber : cyan;
            DrawRect(dark,x,y,w,h);DrawRect(color,x,y,3*s,h);
            Text(d.SubtitleSpeaker==1 ? "HOST  /  BROADCAST" : "INNER VOICE",x+22*s,y+10*s,color,true);
            for(int i=0;i<lines.Count;i++) Text(lines[i],x+22*s,y+(42+i*34)*s,white);
        }
        if(d.GMOpen)
        {
            string[] rows={"GM  /  F1 CLOSE",$"Attempt {d.AttemptId}   Deaths {d.DeathCount}   HP {d.Health:0}   B {d.CheckpointSaved}",
                $"Gun {d.HasGun}  Card {d.HasAccessCard}  Camera {d.CameraLearned}  Puzzle {d.PuzzleSolved}",
                "1 Die / retry     2 TEST ONLY: grant B prerequisites","3 Teleport near B (does not save)",
                "4 Add guard     5 Remove guard (NO reward)","6 Training camera     7 Puzzle camera",
                $"Kills {d.KilledGuards}  Alive {d.LivingGuards}  Reward {d.WaveRewardEligible}",
                $"Dialogue queued {d.DialogueQueueCount}  Vista {d.VistaActive} / played {d.VistaPlayed}"};
            float w=Math.Min(820*s,sizeX-2*m),y=140*s;
            DrawRect(new FLinearColor(.005f,.012f,.02f,.98f),m,y,w,(rows.Length*30+24)*s);
            for(int i=0;i<rows.Length;i++) Text(rows[i],m+14*s,y+(12+i*30)*s,white,true);
        }
        if(d.Transition!=0)
        {
            DrawRect(new FLinearColor(.003f,.007f,.012f,.96f),0,0,sizeX,sizeY);
            Card(d.Transition==1 ? "MEMORY OVERLOAD" : "OFF AIR / REWINDING",sizeY*.46f,white);
            Card(d.Transition==1 ? "The memory is tearing through me..." : "Returning to the last memory anchor...",sizeY*.55f,cyan);
        }
        if(!string.IsNullOrEmpty(d.FailureText)) Card(d.FailureText,sizeY*.3f,red);
    }
}
