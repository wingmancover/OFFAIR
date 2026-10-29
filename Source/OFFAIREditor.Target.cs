using UnrealBuildTool;

public class OFFAIREditorTarget : TargetRules
{
    public OFFAIREditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("OFFAIR");
    }
}
