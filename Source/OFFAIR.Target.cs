using UnrealBuildTool;

public class OFFAIRTarget : TargetRules
{
    public OFFAIRTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("OFFAIR");
    }
}
