"""D4 architecture ported verbatim from the selected training snapshot."""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

# DeepLabv3+ with a MobileNetV2 backbone, adapted for 15-channel flood-segmentation inputs.
# DeepLabv3+ paper: https://arxiv.org/abs/1802.02611
class ConvBNReLU(nn.Module):
    def __init__(self, in_ch, out_ch, ks=3, stride=1, padding=1, dilation=1, groups=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(
                in_ch,
                out_ch,
                kernel_size=ks,
                stride=stride,
                padding=padding,
                dilation=dilation,
                groups=groups,
                bias=False,
            ),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class SeparableConvBNReLU(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1, dilation=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(
                in_ch,
                in_ch,
                kernel_size=3,
                stride=stride,
                padding=dilation,
                dilation=dilation,
                groups=in_ch,
                bias=False,
            ),
            nn.BatchNorm2d(in_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class MobileNetV2DeepLabEncoder(nn.Module):
    def __init__(self, in_channels=15, output_stride=16, pretrained_backbone=True):
        super().__init__()
        if output_stride not in (8, 16):
            raise ValueError("output_stride must be 8 or 16")

        # D4 CHANGE: retain ImageNet layers and adapt only the input convolution.
        weights = MobileNet_V2_Weights.DEFAULT if pretrained_backbone else None
        backbone = mobilenet_v2(weights=weights)
        features = backbone.features
        later_before = {k: v.detach().clone() for k, v in features.state_dict().items()
                        if k != '0.0.weight'} if pretrained_backbone else {}
        self._replace_first_conv(features, in_channels, pretrained_backbone)
        self._set_output_stride(features, output_stride)
        later_after = features.state_dict()
        if pretrained_backbone and not all(torch.equal(value, later_after[key])
                                           for key, value in later_before.items()):
            raise ValueError('Later pretrained backbone weights were modified.')
        self.pretrained_verification = {
            'weights': str(weights) if weights is not None else None,
            'later_layers_preserved': bool(pretrained_backbone),
            'input_channels': in_channels,
            'first_conv_strategy': 'RGB mean repeated across channels, scaled by 3 / input_channels',
            'first_conv_scale': 3.0 / in_channels,
        }
        del later_before, later_after

        feature_blocks = list(features.children())
        self.low_level_features = nn.Sequential(*feature_blocks[:4])
        self.high_level_features = nn.Sequential(*feature_blocks[4:])
        self.low_level_channels = 24
        self.out_channels = 1280

    @staticmethod
    def _replace_first_conv(features, in_channels, pretrained_backbone):
        old_conv = features[0][0]
        features[0][0] = nn.Conv2d(
            in_channels,
            old_conv.out_channels,
            kernel_size=old_conv.kernel_size,
            stride=old_conv.stride,
            padding=old_conv.padding,
            bias=False,
        )
        if pretrained_backbone:
            # Summed response for equal channel values matches the RGB stem:
            # C * (mean_RGB * 3/C) = sum_RGB. No extra random draws are used.
            with torch.no_grad():
                adapted = old_conv.weight.mean(dim=1, keepdim=True).repeat(1, in_channels, 1, 1)
                adapted.mul_(3.0 / in_channels)
                features[0][0].weight.copy_(adapted)

    @staticmethod
    def _make_block_dilated(block, dilation):
        for module in block.modules():
            if isinstance(module, nn.Conv2d) and module.kernel_size == (3, 3):
                if module.stride == (2, 2):
                    module.stride = (1, 1)
                module.dilation = (dilation, dilation)
                module.padding = (dilation, dilation)

    def _set_output_stride(self, features, output_stride):
        if output_stride == 16:
            dilated_blocks = {14: 2, 15: 2, 16: 2, 17: 2}
        else:
            dilated_blocks = {
                7: 2,
                8: 2,
                9: 2,
                10: 2,
                11: 2,
                12: 2,
                13: 2,
                14: 4,
                15: 4,
                16: 4,
                17: 4,
            }

        for block_idx, dilation in dilated_blocks.items():
            self._make_block_dilated(features[block_idx], dilation)

    def forward(self, x):
        low_level = self.low_level_features(x)
        x = self.high_level_features(low_level)
        return x, low_level


class ASPPBranch(nn.Module):
    def __init__(self, in_ch, out_ch, dilation):
        super().__init__()
        if dilation == 1:
            self.block = ConvBNReLU(in_ch, out_ch, ks=1, stride=1, padding=0)
        else:
            self.block = SeparableConvBNReLU(in_ch, out_ch, stride=1, dilation=dilation)

    def forward(self, x):
        return self.block(x)


class ASPPPooling(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.project = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        size = x.shape[2:]
        x = self.pool(x)
        x = self.project(x)
        return F.interpolate(x, size=size, mode="bilinear", align_corners=False)


class ASPP(nn.Module):
    def __init__(self, in_ch, out_ch=256, rates=(6, 12, 18)):
        super().__init__()
        self.branches = nn.ModuleList(
            [ASPPBranch(in_ch, out_ch, dilation=1)]
            + [ASPPBranch(in_ch, out_ch, dilation=rate) for rate in rates]
            + [ASPPPooling(in_ch, out_ch)]
        )
        self.project = nn.Sequential(
            ConvBNReLU(out_ch * len(self.branches), out_ch, ks=1, stride=1, padding=0),
            nn.Dropout(0.1),
        )

    def forward(self, x):
        x = torch.cat([branch(x) for branch in self.branches], dim=1)
        return self.project(x)


class DeepLabV3PlusDecoder(nn.Module):
    def __init__(self, low_ch=128, aspp_ch=256, num_classes=1):
        super().__init__()
        self.low_project = ConvBNReLU(low_ch, 48, ks=1, stride=1, padding=0)
        self.decoder = nn.Sequential(
            SeparableConvBNReLU(aspp_ch + 48, 256),
            SeparableConvBNReLU(256, 256),
            nn.Dropout(0.1),
            nn.Conv2d(256, num_classes, kernel_size=1),
        )

    def forward(self, aspp_features, low_level):
        low_level = self.low_project(low_level)
        aspp_features = F.interpolate(
            aspp_features,
            size=low_level.shape[2:],
            mode="bilinear",
            align_corners=False,
        )
        x = torch.cat([aspp_features, low_level], dim=1)
        return self.decoder(x)


class DeepLabV3Plus(nn.Module):
    def __init__(self, in_channels=15, num_classes=1, output_stride=16, pretrained_backbone=True):
        super().__init__()
        if output_stride == 16:
            # D4 CHANGE: smaller ASPP rates at unchanged output stride 16.
            aspp_rates = (3, 6, 9)
        elif output_stride == 8:
            aspp_rates = (12, 24, 36)
        else:
            raise ValueError("output_stride must be 8 or 16")

        self.encoder = MobileNetV2DeepLabEncoder(in_channels=in_channels, output_stride=output_stride,
                                                   pretrained_backbone=pretrained_backbone)
        self.aspp = ASPP(in_ch=self.encoder.out_channels, out_ch=256, rates=aspp_rates)
        self.decoder = DeepLabV3PlusDecoder(
            low_ch=self.encoder.low_level_channels,
            aspp_ch=256,
            num_classes=num_classes,
        )

    def forward(self, x):
        input_size = x.shape[2:]
        encoder_features, low_level = self.encoder(x)
        aspp_features = self.aspp(encoder_features)
        out = self.decoder(aspp_features, low_level)
        return F.interpolate(out, size=input_size, mode="bilinear", align_corners=False)
