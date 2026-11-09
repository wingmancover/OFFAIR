using UnrealSharp.Attributes;
using UnrealSharp.CoreUObject;
using UnrealSharp.Engine;

namespace Offair.Managed;

/// <summary>Readable prototype HUD; debug content appears only behind F1. Final art/dialogue is step 5.</summary>
[UClass]
public partial class ARegionHUD : AHUD
{
    [UProperty(PropertyFlags.EditAnywhere)] public partial UFont PlayFont { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UFont SmallPlayFont { get; set; }
    private ARegionLoopDirector? director;
    public override void ReceiveDrawHUD(int sizeX, int sizeY)
    {
        if (director is null || !SystemLibrary.IsValid(director))
        {
            UGameplayStatics.GetAllActorsOfClass<ARegionLoopDirector>(out var found);
            director = found.FirstOrDefault();
        }
        if (director is null) return;
        var d = director;
        float scale = Math.Clamp(sizeX / 1600f, .65f, 1.7f);
        void Text(string s, float x, float y, FLinearColor color, float font = 1)
            => DrawText(s, color, x, y, font < 1 ? SmallPlayFont : PlayFont, 1);
        var white = new FLinearColor(.96f,.98f,1,1);
        var cyan = new FLinearColor(.3f,.86f,1,1);
        var dark = new FLinearColor(.007f,.016f,.025f,.94f);
        void Panel(string s, float y, FLinearColor color)
        {
            var lines = new List<string>(); string line = "";
            foreach (var word in s.Split(' '))
            {
                var candidate = line.Length == 0 ? word : line + " " + word;
                GetTextSize(candidate, out var width, out _, PlayFont, 1);
                if (width > sizeX - 80 && line.Length > 0) { lines.Add(line); line = word; }
                else line = candidate;
            }
            lines.Add(line);
            GetTextSize("Ag", out _, out var lineHeight, PlayFont, 1);
            float spacing = lineHeight + 4;
            // Wrap upward, keeping host and inner-thought subtitles in separate bottom slots.
            for (int i=0; i<lines.Count; i++)
            {
                GetTextSize(lines[i],out var w,out _,PlayFont,1);
                float x=(sizeX-w)/2, top=y-(lines.Count-1-i)*spacing;
                DrawRect(dark,x-16,top-4,w+32,spacing);
                Text(lines[i],x,top,color);
            }
        }
        DrawRect(white,sizeX/2f-3,sizeY/2f-1,6,2);
        string objective = d.CheckpointSaved ? "MEMORY B / SESSION SAVED" : !d.MemoryExperienced ? "FIND THE RED NOTE"
            : !d.HasGun ? "CHOOSE A WEAPON" : d.LivingGuards > 0 ? $"CLEAR THE ROOM / {d.LivingGuards} GUARDS"
            : !d.HasAccessCard ? "COLLECT THE ACCESS CARD" : !d.CameraLearned ? "TAKE CONTROL OF THE TRAINING CAMERA"
            : d.PuzzleSolved ? "RECOVER MEMORY B BEYOND THE DOOR" : d.InPuzzleRoom || d.PuzzleRemote ? "FIND THE PATTERN / SHOOT / SUBMIT" : "ENTER THE SIGNAL LAB";
        const string controls="WASD Move   SPACE Jump   E Interact   LMB Fire   F1 GM";
        GetTextSize(objective,out var objectiveWidth,out var objectiveHeight,PlayFont,1);
        GetTextSize(controls,out var controlsWidth,out var controlsHeight,SmallPlayFont,1);
        float left=20*scale, topEdge=20*scale, controlsY=topEdge+objectiveHeight+14;
        DrawRect(dark,left,topEdge,Math.Max(objectiveWidth,controlsWidth)+24,objectiveHeight+controlsHeight+24);
        Text(objective,left+12,topEdge+6,white);
        Text(controls,left+12,controlsY,cyan,.72f);
        string health=$"HEALTH {Math.Ceiling(d.Health)} / {d.MaximumHealth:0}"+(d.HasGun ? $"    AMMO {d.Ammo}" : "");
        GetTextSize(health,out var healthWidth,out var healthHeight,SmallPlayFont,1);
        DrawRect(dark,left,sizeY-72*scale,healthWidth+24,healthHeight+16);
        Text(health,left+12,sizeY-72*scale+6,white,.8f);
        if (!string.IsNullOrEmpty(d.PromptText)) Panel(d.PromptText,sizeY*.70f,white);
        if (!string.IsNullOrEmpty(d.HostText)) Panel("HOST: " + d.HostText,sizeY-180*scale,new FLinearColor(1,.75f,.3f,1));
        if (!string.IsNullOrEmpty(d.ThoughtText)) Panel(d.ThoughtText,sizeY-124*scale,cyan);
        if (d.RemoteActive) Panel(d.PuzzleRemote ? (d.PatternAligned ? "SIGNAL ALIGNED / Remember the pattern / E or Q to return"
            : "SIGNAL CAMERA / Find the cyan fragments and center them / E or Q to return")
            : d.LessonTurned ? "CAMERA / E or Q to return" : "CAMERA / Move mouse to look around / E or Q to return",controlsY+controlsHeight+30,cyan);
        if (d.InPuzzleRoom && !d.RemoteActive && !d.PuzzleSolved && !d.PuzzleSubmitting)
            Panel("Shoot tiles to toggle / Clear is safe / Only SUBMIT judges your answer",controlsY+controlsHeight+30,cyan);
        if (!string.IsNullOrEmpty(d.PuzzleStatus)) Panel(d.PuzzleStatus,sizeY*.38f,d.PuzzleSubmitting ? new FLinearColor(1,.3f,.2f,1) : cyan);
        if (d.GMOpen)
        {
            DrawRect(dark,20*scale,150*scale,790*scale,330*scale);
            string[] rows = {
                "GM / TEACHING ROOM - F1 CLOSE",
                $"Attempt {d.AttemptId}   Deaths {d.DeathCount}   HP {d.Health:0}   B {d.CheckpointSaved}",
                $"Gun {d.HasGun}   Card {d.HasAccessCard}   Camera {d.CameraLearned}   Puzzle {d.PuzzleSolved}",
                "1  Die / retry     2  TEST ONLY: grant B prerequisites",
                "3  Teleport near B (does not save)",
                "4  Add guard (teaching fight only)",
                "5  Remove guard (NO kill credit / NO card reward)",
                "6  Training camera / 7  Puzzle camera",
                $"Kills {d.KilledGuards}  Alive {d.LivingGuards}  Card reward eligible {d.WaveRewardEligible}"
            };
            for (int i=0;i<rows.Length;i++) DrawText(rows[i],white,32*scale,(164+i*32)*scale,null,1.7f*scale);
        }
        if (d.Transition != 0)
        {
            DrawRect(new FLinearColor(.005f,.008f,.015f,.90f),0,0,sizeX,sizeY);
            Panel(d.Transition == 1 ? "MEMORY OVERLOAD" : "OFF AIR / REWINDING",sizeY*.45f,white);
            Panel(d.Transition == 1 ? "The memory is tearing through me..." : "Returning to the last memory anchor...",sizeY*.53f,cyan);
        }
        if (!string.IsNullOrEmpty(d.FailureText)) Panel(d.FailureText,sizeY*.25f,new FLinearColor(1,.25f,.2f,1));
    }
}
